from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterator

import fcntl


class BusyPaths:
    """
    Centraliza las rutas del runtime local de BuSy usando `.busy`
    como artefacto persistente y un workspace temporal como runtime vivo.
    """

    DEFAULT_STRUCTURE: dict[str, tuple[str, ...]] = {
        "meta": (),
        "db": (),
        "storage": ("images", "videos", "documents", "receipts", "misc"),
        "config": (),
        "logs": (),
        "backups": (),
        "tmp": (),
    }

    SQLITE_SUFFIXES: tuple[str, ...] = (".sqlite3", ".sqlite", ".db")
    SQLITE_SIDECAR_SUFFIXES: tuple[str, ...] = ("-wal", "-shm", "-journal")

    def __init__(self, root_dir: str | Path | None = None) -> None:
        self.project_root = Path(root_dir or Path.cwd()).resolve()
        self.archive_path = self._resolve_archive_path()
        self._runtime_root = self._resolve_runtime_root()
        self._runtime_state_path = self._resolve_runtime_state_path()
        self._archive_lock_path = self._resolve_archive_lock_path()
        self._bootstrapped = False

    def bootstrap(self) -> Path:
        if self._bootstrapped and self._runtime_manifest_path().exists():
            return self._runtime_root

        with self._archive_lock():
            self._bootstrap_locked()

        self._bootstrapped = True
        return self._runtime_root

    @property
    def busy_root(self) -> Path:
        self.bootstrap()
        return self._runtime_root

    @property
    def runtime_root(self) -> Path:
        return self.busy_root

    @property
    def manifest_path(self) -> Path:
        self.bootstrap()
        return self._runtime_manifest_path()

    @property
    def database_path(self) -> Path:
        return self.resolve_database_path()

    @property
    def settings_path(self) -> Path:
        self.bootstrap()
        return self._runtime_settings_path()

    @property
    def env_path(self) -> Path:
        self.bootstrap()
        return self._runtime_env_path()

    @property
    def env_example_path(self) -> Path:
        self.bootstrap()
        return self._runtime_env_example_path()

    @property
    def legacy_root(self) -> Path:
        return self.project_root / "legacy"

    @property
    def legacy_database_dir(self) -> Path:
        return self.legacy_root / "db"

    @property
    def legacy_logs_dir(self) -> Path:
        return self.legacy_root / "logs"

    @property
    def legacy_database_path(self) -> Path:
        return self.legacy_database_dir / "systemDB.db"

    def resolve_storage_path(self, category: str, filename: str | None = None) -> Path:
        normalized_category = category.strip().lower()
        allowed = self.DEFAULT_STRUCTURE["storage"]
        if normalized_category not in allowed:
            raise ValueError(f"Storage category not supported: {category}")

        base_path = self.busy_root / "storage" / normalized_category
        return base_path if filename is None else base_path / filename

    def resolve_database_path(self, filename: str = "main.sqlite3") -> Path:
        return self.busy_root / "db" / filename

    def resolve_log_path(self, filename: str) -> Path:
        normalized_name = self._normalize_filename(filename, default_suffix=".csv")
        return self.busy_root / "logs" / normalized_name

    def resolve_legacy_log_path(self, filename: str) -> Path:
        normalized_name = self._normalize_filename(filename, default_suffix=".csv")
        return self.legacy_logs_dir / normalized_name

    def resolve_path(self, *parts: str) -> Path:
        if not parts:
            return self.busy_root
        return self.busy_root.joinpath(*parts)

    def ensure_runtime_database(self, filename: str = "main.sqlite3") -> Path:
        runtime_path = self.resolve_database_path(filename)
        runtime_path.parent.mkdir(parents=True, exist_ok=True)
        return runtime_path

    def ensure_runtime_log(self, filename: str) -> Path:
        runtime_path = self.resolve_log_path(filename)
        legacy_path = self.resolve_legacy_log_path(filename)
        self._copy_if_missing(runtime_path, legacy_path)
        runtime_path.parent.mkdir(parents=True, exist_ok=True)
        if not runtime_path.exists():
            runtime_path.touch()
        return runtime_path

    def is_managed_path(self, path: str | Path) -> bool:
        try:
            Path(path).resolve().relative_to(self._runtime_root)
            return True
        except ValueError:
            return False

    def flush_archive(self) -> Path:
        self.bootstrap()
        with self._archive_lock():
            self._ensure_runtime_defaults_locked()
            self._refresh_manifest_locked()
            self._write_archive_locked()
        return self.archive_path

    def cleanup(self) -> None:
        with self._archive_lock():
            self._cleanup_locked()
        self._bootstrapped = False

    def _bootstrap_locked(self) -> None:
        state = self._load_runtime_state_locked()
        pids = self._prune_dead_pids(state.get("pids", []))
        current_pid = os.getpid()
        had_live_pids = bool(pids)

        if current_pid not in pids:
            pids.append(current_pid)

        if not had_live_pids:
            self._reset_runtime_locked()
            if self.archive_path.exists():
                self._extract_archive_locked()
            else:
                self._ensure_runtime_defaults_locked()
                self._refresh_manifest_locked()
                self._write_archive_locked()
        else:
            self._runtime_root.mkdir(parents=True, exist_ok=True)
            if not self._runtime_manifest_path().exists():
                if self.archive_path.exists():
                    self._reset_runtime_locked()
                    self._extract_archive_locked()
                else:
                    self._ensure_runtime_defaults_locked()
                    self._refresh_manifest_locked()
                    self._write_archive_locked()
            else:
                self._ensure_runtime_defaults_locked()

        self._write_runtime_state_locked(
            {
                "runtime_root": str(self._runtime_root),
                "pids": pids,
            }
        )

    def _cleanup_locked(self) -> None:
        state = self._load_runtime_state_locked()
        current_pid = os.getpid()
        remaining_pids = [
            pid
            for pid in self._prune_dead_pids(state.get("pids", []))
            if pid != current_pid
        ]

        if remaining_pids:
            self._write_runtime_state_locked(
                {
                    "runtime_root": str(self._runtime_root),
                    "pids": remaining_pids,
                }
            )
            return

        if self._runtime_root.exists():
            shutil.rmtree(self._runtime_root, ignore_errors=True)

        if self._runtime_state_path.exists():
            self._runtime_state_path.unlink()

    def _resolve_archive_path(self) -> Path:
        configured = os.getenv("BUSY_ARCHIVE_PATH", ".busy")
        archive_path = Path(configured).expanduser()
        if not archive_path.is_absolute():
            archive_path = self.project_root / archive_path
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        return archive_path.resolve()

    def _resolve_runtime_root(self) -> Path:
        configured = os.getenv("BUSY_RUNTIME_DIR")
        if configured:
            runtime_path = Path(configured).expanduser()
            if not runtime_path.is_absolute():
                runtime_path = self.project_root / runtime_path
            return runtime_path.resolve()

        digest = sha256(str(self.archive_path).encode("utf-8")).hexdigest()[:12]
        return (Path(tempfile.gettempdir()) / f"busy-runtime-{digest}").resolve()

    def _resolve_runtime_state_path(self) -> Path:
        return self.archive_path.with_name(f"{self._archive_basename()}.runtime.json")

    def _resolve_archive_lock_path(self) -> Path:
        return self.archive_path.with_name(f"{self._archive_basename()}.lock")

    def _archive_basename(self) -> str:
        if self.archive_path.name.lower().endswith(".zip"):
            return self.archive_path.name[:-4]
        return self.archive_path.stem

    def _runtime_manifest_path(self) -> Path:
        return self._runtime_root / "meta" / "manifest.json"

    def _runtime_settings_path(self) -> Path:
        return self._runtime_root / "config" / "settings.json"

    def _runtime_env_path(self) -> Path:
        return self._runtime_root / "config" / "app.env"

    def _runtime_env_example_path(self) -> Path:
        return self._runtime_root / "config" / "app.env.example"

    @contextmanager
    def _archive_lock(self) -> Iterator[None]:
        self._archive_lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self._archive_lock_path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _load_runtime_state_locked(self) -> dict[str, Any]:
        if not self._runtime_state_path.exists():
            return {
                "runtime_root": str(self._runtime_root),
                "pids": [],
            }

        try:
            payload = json.loads(self._runtime_state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {
                "runtime_root": str(self._runtime_root),
                "pids": [],
            }

        if not isinstance(payload, dict):
            return {
                "runtime_root": str(self._runtime_root),
                "pids": [],
            }

        return payload

    def _write_runtime_state_locked(self, payload: dict[str, Any]) -> None:
        self._runtime_state_path.parent.mkdir(parents=True, exist_ok=True)
        self._runtime_state_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )

    def _prune_dead_pids(self, pids: list[Any]) -> list[int]:
        live_pids: list[int] = []
        for raw_pid in pids:
            try:
                pid = int(raw_pid)
            except (TypeError, ValueError):
                continue

            if self._pid_is_alive(pid):
                live_pids.append(pid)

        return live_pids

    def _pid_is_alive(self, pid: int) -> bool:
        if pid <= 0:
            return False

        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def _reset_runtime_locked(self) -> None:
        if self._runtime_root.exists():
            shutil.rmtree(self._runtime_root, ignore_errors=True)
        self._runtime_root.mkdir(parents=True, exist_ok=True)

    def _extract_archive_locked(self) -> None:
        if not self.archive_path.exists():
            return

        try:
            with zipfile.ZipFile(self.archive_path, mode="r") as archive:
                archive.extractall(self._runtime_root)
        except zipfile.BadZipFile as exc:
            raise RuntimeError(
                f"El archivo de persistencia '{self.archive_path.name}' esta corrupto."
            ) from exc

        self._ensure_runtime_defaults_locked()

    def _ensure_runtime_defaults_locked(self) -> None:
        self._runtime_root.mkdir(parents=True, exist_ok=True)

        for folder, children in self.DEFAULT_STRUCTURE.items():
            base_path = self._runtime_root / folder
            base_path.mkdir(parents=True, exist_ok=True)
            self._ensure_keep_file(base_path)
            for child in children:
                child_path = base_path / child
                child_path.mkdir(parents=True, exist_ok=True)
                self._ensure_keep_file(child_path)

        self._ensure_file(
            self._runtime_manifest_path(),
            self._default_manifest(),
        )
        self._ensure_file(
            self._runtime_settings_path(),
            self._default_settings(),
        )
        self._ensure_env_example()

    def _ensure_file(self, path: Path, default_content: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            return
        path.write_text(
            json.dumps(default_content, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )

    def _ensure_env_example(self) -> None:
        env_example_path = self._runtime_env_example_path()
        env_example_path.parent.mkdir(parents=True, exist_ok=True)
        if env_example_path.exists():
            return
        content = (
            "# BuSy local runtime environment\n"
            "BUSY_ENV=development\n"
            f"BUSY_ARCHIVE_PATH={self.archive_path}\n"
            f"BUSY_RUNTIME_DIR={self._runtime_root}\n"
            f"BUSY_DB_PATH={self._runtime_root / 'db' / 'main.sqlite3'}\n"
            "BUSY_LOG_LEVEL=INFO\n"
        )
        env_example_path.write_text(content, encoding="utf-8")

    def _ensure_keep_file(self, path: Path) -> None:
        keep_path = path / ".keep"
        if not keep_path.exists():
            keep_path.write_text("", encoding="utf-8")

    def _copy_if_missing(self, destination: Path, source: Path) -> None:
        if destination.exists() or not source.exists():
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    def _normalize_filename(self, filename: str, *, default_suffix: str) -> str:
        normalized = filename.strip()
        if not normalized:
            raise ValueError("Filename cannot be empty")
        if not normalized.lower().endswith(default_suffix):
            normalized = f"{normalized}{default_suffix}"
        return normalized

    def _refresh_manifest_locked(self) -> None:
        manifest_path = self._runtime_manifest_path()
        default_manifest = self._default_manifest()

        try:
            current_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(current_manifest, dict):
                current_manifest = {}
        except (FileNotFoundError, json.JSONDecodeError):
            current_manifest = {}

        current_manifest.setdefault("created_at", default_manifest["created_at"])
        current_manifest["app"] = default_manifest["app"]
        current_manifest["version"] = default_manifest["version"]
        current_manifest["instance_id"] = default_manifest["instance_id"]
        current_manifest["paths"] = default_manifest["paths"]
        current_manifest["updated_at"] = datetime.now(timezone.utc).isoformat()

        manifest_path.write_text(
            json.dumps(current_manifest, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )

    def _write_archive_locked(self) -> None:
        self.archive_path.parent.mkdir(parents=True, exist_ok=True)

        temp_archive = self.archive_path.with_name(f"{self.archive_path.name}.tmp")
        snapshot_root = Path(
            tempfile.mkdtemp(prefix="busy-archive-snapshots-", dir=str(self._runtime_root.parent))
        )

        try:
            db_snapshots = self._build_database_snapshots(snapshot_root)
            snapshot_relpaths = set(db_snapshots.keys())

            with zipfile.ZipFile(
                temp_archive,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
            ) as archive:
                for file_path in sorted(self._runtime_root.rglob("*")):
                    if not file_path.is_file():
                        continue

                    relative_path = file_path.relative_to(self._runtime_root)
                    if self._should_skip_live_database_file(relative_path, snapshot_relpaths):
                        continue

                    archive.write(file_path, arcname=relative_path.as_posix())

                for relative_name, snapshot_path in sorted(db_snapshots.items()):
                    archive.write(snapshot_path, arcname=relative_name)

            temp_archive.replace(self.archive_path)
        finally:
            if temp_archive.exists():
                temp_archive.unlink()
            shutil.rmtree(snapshot_root, ignore_errors=True)

    def _build_database_snapshots(self, snapshot_root: Path) -> dict[str, Path]:
        snapshots: dict[str, Path] = {}
        database_root = self._runtime_root / "db"

        if not database_root.exists():
            return snapshots

        for file_path in sorted(database_root.rglob("*")):
            if not file_path.is_file() or not self._is_sqlite_database_file(file_path):
                continue

            relative_path = file_path.relative_to(self._runtime_root)
            snapshot_path = snapshot_root / relative_path
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            self._snapshot_sqlite_database(file_path, snapshot_path)
            snapshots[relative_path.as_posix()] = snapshot_path

        return snapshots

    def _snapshot_sqlite_database(self, source_path: Path, destination_path: Path) -> None:
        if destination_path.exists():
            destination_path.unlink()

        with sqlite3.connect(str(source_path)) as source_connection:
            with sqlite3.connect(str(destination_path)) as destination_connection:
                source_connection.backup(destination_connection)

    def _is_sqlite_database_file(self, path: Path) -> bool:
        return path.suffix.lower() in self.SQLITE_SUFFIXES

    def _should_skip_live_database_file(
        self,
        relative_path: Path,
        snapshot_relpaths: set[str],
    ) -> bool:
        relative_name = relative_path.as_posix()
        if relative_name in snapshot_relpaths:
            return True

        for snapshot_name in snapshot_relpaths:
            for suffix in self.SQLITE_SIDECAR_SUFFIXES:
                if relative_name == f"{snapshot_name}{suffix}":
                    return True

        return False

    def _default_manifest(self) -> dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        return {
            "app": "BuSy",
            "version": 1,
            "created_at": timestamp,
            "updated_at": timestamp,
            "instance_id": os.getenv("BUSY_INSTANCE_ID", ""),
            "paths": {
                "database": str(self._runtime_root / "db" / "main.sqlite3"),
                "settings": str(self._runtime_settings_path()),
                "storage": str(self._runtime_root / "storage"),
                "logs": str(self._runtime_root / "logs"),
                "backups": str(self._runtime_root / "backups"),
                "tmp": str(self._runtime_root / "tmp"),
            },
        }

    def _default_settings(self) -> dict[str, Any]:
        return {
            "app_name": "BuSy",
            "environment": os.getenv("BUSY_ENV", "development"),
            "storage_strategy": "local",
            "database": {
                "engine": "sqlite",
                "path": str(self._runtime_root / "db" / "main.sqlite3"),
            },
            "files": {
                "root": str(self._runtime_root / "storage"),
                "categories": list(self.DEFAULT_STRUCTURE["storage"]),
            },
            "logs": {
                "root": str(self._runtime_root / "logs"),
                "level": os.getenv("BUSY_LOG_LEVEL", "INFO"),
            },
        }


class Document:
    """
    Manejador simple para archivos dentro del runtime persistido en `.busy`.
    """

    def __init__(
        self,
        doc_name: str,
        *,
        category: str = "documents",
        root_dir: str | Path | None = None,
        create_on_init: bool = False,
    ) -> None:
        if not doc_name.strip():
            raise ValueError("Document name cannot be empty")

        self.doc_name = doc_name
        self.paths = BusyPaths(root_dir=root_dir)
        self.paths.bootstrap()
        self.path = self.paths.resolve_storage_path(category, doc_name)

        if create_on_init:
            self._createDoc()

    def retrieveDoc(self, create_if_missing: bool = True) -> Path:
        if create_if_missing and not self.path.exists():
            self._createDoc()
        return self.path

    def read(self, *, default: str = "") -> str:
        file_path = self.retrieveDoc(create_if_missing=False)
        if not file_path.exists():
            return default
        return file_path.read_text(encoding="utf-8")

    def write(self, content: str, *, overwrite: bool = True) -> Path:
        file_path = self.retrieveDoc()
        current_content = ""
        if file_path.exists() and not overwrite:
            current_content = file_path.read_text(encoding="utf-8")
        file_path.write_text(current_content + content, encoding="utf-8")
        self.paths.flush_archive()
        return file_path

    def write_json(self, payload: dict[str, Any] | list[Any]) -> Path:
        file_path = self.retrieveDoc()
        file_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )
        self.paths.flush_archive()
        return file_path

    def saveDoc(self, content: str) -> Path:
        return self.write(content, overwrite=True)

    def delete(self, *, missing_ok: bool = True) -> None:
        if self.path.exists():
            self.path.unlink()
            self.paths.flush_archive()
            return
        if not missing_ok:
            raise FileNotFoundError(self.path)

    def _createDoc(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        created = not self.path.exists()
        self.path.touch(exist_ok=True)
        if created:
            self.paths.flush_archive()
        return self.path


def bootstrap_busy_workspace(root_dir: str | Path | None = None) -> BusyPaths:
    paths = BusyPaths(root_dir=root_dir)
    paths.bootstrap()
    return paths
