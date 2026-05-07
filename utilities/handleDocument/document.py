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


# IMPORTANT:
# Any change to the persisted .busy archive structure must add a migration and
# bump CURRENT_BUSY_FORMAT_VERSION. Examples: new required config files,
# renamed paths, new storage folders, or manifest/settings/sysconfig shape changes.
CURRENT_BUSY_FORMAT_VERSION = 2

# IMPORTANT:
# Any SQLite schema change must add a DB migration and bump
# CURRENT_DATABASE_SCHEMA_VERSION. SQLite uses PRAGMA user_version as source
# of truth for the active database schema version.
CURRENT_DATABASE_SCHEMA_VERSION = 2


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
    CURRENT_BUSY_FORMAT_VERSION = CURRENT_BUSY_FORMAT_VERSION
    CURRENT_DATABASE_SCHEMA_VERSION = CURRENT_DATABASE_SCHEMA_VERSION

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
    def sysconfig_path(self) -> Path:
        self.bootstrap()
        return self._runtime_sysconfig_path()

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

    def create_archive_backup(self) -> Path:
        with self._archive_lock():
            return self._create_archive_backup_locked()

    def restore_archive_backup(self, backup_path: str | Path) -> None:
        with self._archive_lock():
            self._restore_archive_backup_locked(Path(backup_path))

    def update_database_schema_version(
        self,
        version: int = CURRENT_DATABASE_SCHEMA_VERSION,
    ) -> Path:
        self.bootstrap()
        with self._archive_lock():
            manifest = self._read_manifest_locked()
            manifest["database_schema_version"] = version
            self._write_manifest_locked(manifest)
            self._refresh_manifest_locked()
            self._write_archive_locked()
        return self.archive_path

    def upgrade_if_needed(self) -> bool:
        self.bootstrap()
        with self._archive_lock():
            return self._upgrade_if_needed_locked()

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
            self._upgrade_if_needed_locked()
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
            self._upgrade_if_needed_locked()

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

    def _runtime_sysconfig_path(self) -> Path:
        return self._runtime_root / "config" / "sysconfig.json"

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
        # Defaults are only for new or missing files. Existing .busy archives
        # must be upgraded through versioned migrations, not by this method alone.
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
        self._ensure_file(
            self._runtime_sysconfig_path(),
            self._default_sysconfig(),
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

    def _upgrade_if_needed_locked(self) -> bool:
        manifest = self._read_manifest_locked()
        current_version = self._manifest_int(
            manifest,
            "busy_format_version",
            default=0,
        )

        if current_version > self.CURRENT_BUSY_FORMAT_VERSION:
            raise RuntimeError(
                "El archivo de persistencia requiere una version mas nueva de BuSy."
            )

        if current_version == self.CURRENT_BUSY_FORMAT_VERSION:
            return False

        backup_path = self._create_archive_backup_locked() if self.archive_path.exists() else None

        try:
            while current_version < self.CURRENT_BUSY_FORMAT_VERSION:
                if current_version == 0:
                    self._migrate_busy_format_0_to_1_locked()
                    current_version = 1
                    continue
                if current_version == 1:
                    self._migrate_busy_format_1_to_2_locked()
                    current_version = 2
                    continue

                raise RuntimeError(
                    f"No existe migracion para .busy version {current_version}."
                )

            self._refresh_manifest_locked()
            self._write_archive_locked()
            return True
        except Exception as exc:
            if backup_path is not None:
                self._restore_archive_backup_locked(backup_path)
            raise RuntimeError(
                f"No se pudo migrar '{self.archive_path.name}'. Se restauro el backup."
            ) from exc

    def _migrate_busy_format_0_to_1_locked(self) -> None:
        self._ensure_runtime_defaults_locked()
        self._merge_settings_locked()

        manifest = self._read_manifest_locked()
        manifest["busy_format_version"] = self.CURRENT_BUSY_FORMAT_VERSION
        manifest.setdefault(
            "database_schema_version",
            self.CURRENT_DATABASE_SCHEMA_VERSION,
        )
        self._write_manifest_locked(manifest)

    def _migrate_busy_format_1_to_2_locked(self) -> None:
        self._ensure_runtime_defaults_locked()
        self._merge_sysconfig_locked()

        manifest = self._read_manifest_locked()
        manifest["busy_format_version"] = self.CURRENT_BUSY_FORMAT_VERSION
        self._write_manifest_locked(manifest)

    def _merge_settings_locked(self) -> None:
        settings_path = self._runtime_settings_path()
        default_settings = self._default_settings()

        try:
            current_settings = json.loads(settings_path.read_text(encoding="utf-8"))
            if not isinstance(current_settings, dict):
                current_settings = {}
        except (FileNotFoundError, json.JSONDecodeError):
            current_settings = {}

        merged = self._deep_merge(default_settings, current_settings)
        merged.setdefault("database", {})
        merged.setdefault("files", {})
        merged.setdefault("logs", {})
        if not isinstance(merged["database"], dict):
            merged["database"] = {}
        if not isinstance(merged["files"], dict):
            merged["files"] = {}
        if not isinstance(merged["logs"], dict):
            merged["logs"] = {}

        merged["database"]["path"] = default_settings["database"]["path"]
        merged["files"]["root"] = default_settings["files"]["root"]
        merged["logs"]["root"] = default_settings["logs"]["root"]
        merged["files"]["categories"] = self._merge_unique_list(
            current_settings.get("files", {}).get("categories", [])
            if isinstance(current_settings.get("files"), dict)
            else [],
            default_settings["files"]["categories"],
        )

        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps(merged, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )

    def _merge_sysconfig_locked(self) -> None:
        sysconfig_path = self._runtime_sysconfig_path()
        default_sysconfig = self._default_sysconfig()

        try:
            current_sysconfig = json.loads(sysconfig_path.read_text(encoding="utf-8"))
            if not isinstance(current_sysconfig, dict):
                current_sysconfig = {}
        except (FileNotFoundError, json.JSONDecodeError):
            current_sysconfig = {}

        merged = self._deep_merge(default_sysconfig, current_sysconfig)
        sysconfig_path.parent.mkdir(parents=True, exist_ok=True)
        sysconfig_path.write_text(
            json.dumps(merged, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )

    def _deep_merge(self, defaults: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
        merged: dict[str, Any] = dict(defaults)
        for key, value in current.items():
            default_value = merged.get(key)
            if isinstance(default_value, dict) and isinstance(value, dict):
                merged[key] = self._deep_merge(default_value, value)
            else:
                merged[key] = value
        return merged

    def _merge_unique_list(self, current: Any, defaults: list[Any]) -> list[Any]:
        merged: list[Any] = []
        for value in list(current or []) + list(defaults):
            if value not in merged:
                merged.append(value)
        return merged

    def _create_archive_backup_locked(self) -> Path:
        if not self.archive_path.exists():
            raise FileNotFoundError(self.archive_path)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup_path = self.archive_path.with_name(
            f"{self.archive_path.name}.backup-{timestamp}"
        )
        counter = 1
        while backup_path.exists():
            backup_path = self.archive_path.with_name(
                f"{self.archive_path.name}.backup-{timestamp}-{counter:02d}"
            )
            counter += 1

        shutil.copy2(self.archive_path, backup_path)
        return backup_path

    def _restore_archive_backup_locked(self, backup_path: Path) -> None:
        if not backup_path.exists():
            raise FileNotFoundError(backup_path)

        self.archive_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_path, self.archive_path)

        if self._runtime_root.exists():
            shutil.rmtree(self._runtime_root, ignore_errors=True)
        if self._runtime_state_path.exists():
            self._runtime_state_path.unlink()
        self._bootstrapped = False

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

    def _read_manifest_locked(self) -> dict[str, Any]:
        manifest_path = self._runtime_manifest_path()
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(manifest, dict):
                return manifest
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return {}

    def _write_manifest_locked(self, manifest: dict[str, Any]) -> None:
        manifest_path = self._runtime_manifest_path()
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )

    def _manifest_int(
        self,
        manifest: dict[str, Any],
        key: str,
        *,
        default: int,
    ) -> int:
        try:
            return int(manifest.get(key, default))
        except (TypeError, ValueError):
            return default

    def _refresh_manifest_locked(self) -> None:
        default_manifest = self._default_manifest()
        current_manifest = self._read_manifest_locked()

        current_manifest.setdefault("created_at", default_manifest["created_at"])
        current_manifest["app"] = default_manifest["app"]
        current_manifest["version"] = default_manifest["version"]
        current_manifest["busy_format_version"] = self.CURRENT_BUSY_FORMAT_VERSION
        current_manifest.setdefault(
            "database_schema_version",
            self.CURRENT_DATABASE_SCHEMA_VERSION,
        )
        current_manifest["instance_id"] = default_manifest["instance_id"]
        current_manifest["paths"] = default_manifest["paths"]
        current_manifest["updated_at"] = datetime.now(timezone.utc).isoformat()

        self._write_manifest_locked(current_manifest)

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
            "busy_format_version": self.CURRENT_BUSY_FORMAT_VERSION,
            "database_schema_version": self.CURRENT_DATABASE_SCHEMA_VERSION,
            "created_at": timestamp,
            "updated_at": timestamp,
            "instance_id": os.getenv("BUSY_INSTANCE_ID", ""),
            "paths": {
                "database": str(self._runtime_root / "db" / "main.sqlite3"),
                "settings": str(self._runtime_settings_path()),
                "sysconfig": str(self._runtime_sysconfig_path()),
                "storage": str(self._runtime_root / "storage"),
                "logs": str(self._runtime_root / "logs"),
                "backups": str(self._runtime_root / "backups"),
                "tmp": str(self._runtime_root / "tmp"),
            },
        }

    def _default_sysconfig(self) -> dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        return {
            "system": {
                "name": "BuSy",
                "description": "Business System",
                "environment": os.getenv("BUSY_ENV", "development"),
                "timezone": "America/Mexico_City",
                "locale": "es-MX",
                "maintenance_mode": False,
            },
            "ui": {
                "theme": "default",
                "public_base_path": "/",
                "logo_path": "",
                "favicon_path": "",
            },
            "security": {
                "session_timeout_minutes": 60,
                "allow_public_registration": False,
                "password_min_length": 8,
            },
            "limits": {
                "max_upload_mb": 25,
                "max_search_results": 50,
            },
            "modules": {
                "authentication": True,
                "userconf": True,
                "sysconf": True,
                "scheduler": True,
            },
            "metadata": {
                "version": 1,
                "created_by": "system",
                "updated_by": "system",
                "created_at": timestamp,
                "updated_at": timestamp,
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
