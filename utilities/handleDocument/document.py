from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class BusyPaths:
    """
    Centraliza las rutas del runtime local de BuSy dentro de `.busy/`.
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

    def __init__(self, root_dir: str | Path | None = None) -> None:
        self.project_root = Path(root_dir or Path.cwd()).resolve()
        self.busy_root = self.project_root / ".busy"

    def bootstrap(self) -> Path:
        for folder, children in self.DEFAULT_STRUCTURE.items():
            base_path = self.busy_root / folder
            base_path.mkdir(parents=True, exist_ok=True)
            for child in children:
                child_path = base_path / child
                child_path.mkdir(parents=True, exist_ok=True)
                self._ensure_keep_file(child_path)

        self._ensure_file(
            self.manifest_path,
            self._default_manifest(),
        )
        self._ensure_file(
            self.settings_path,
            self._default_settings(),
        )
        self._ensure_env_example()
        return self.busy_root

    @property
    def manifest_path(self) -> Path:
        return self.busy_root / "meta" / "manifest.json"

    @property
    def database_path(self) -> Path:
        return self.resolve_database_path()

    @property
    def settings_path(self) -> Path:
        return self.busy_root / "config" / "settings.json"

    @property
    def env_path(self) -> Path:
        return self.busy_root / "config" / "app.env"

    @property
    def env_example_path(self) -> Path:
        return self.busy_root / "config" / "app.env.example"

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
        self.bootstrap()
        runtime_path = self.resolve_database_path(filename)
        runtime_path.parent.mkdir(parents=True, exist_ok=True)
        return runtime_path

    def ensure_runtime_log(self, filename: str) -> Path:
        self.bootstrap()
        runtime_path = self.resolve_log_path(filename)
        legacy_path = self.resolve_legacy_log_path(filename)
        self._copy_if_missing(runtime_path, legacy_path)
        runtime_path.parent.mkdir(parents=True, exist_ok=True)
        if not runtime_path.exists():
            runtime_path.touch()
        return runtime_path

    def _ensure_file(self, path: Path, default_content: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            return
        path.write_text(
            json.dumps(default_content, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )

    def _ensure_env_example(self) -> None:
        self.env_example_path.parent.mkdir(parents=True, exist_ok=True)
        if self.env_example_path.exists():
            return
        content = (
            "# BuSy local runtime environment\n"
            "BUSY_ENV=development\n"
            f"BUSY_DB_PATH={self.database_path}\n"
            "BUSY_LOG_LEVEL=INFO\n"
        )
        self.env_example_path.write_text(content, encoding="utf-8")

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

    def _default_manifest(self) -> dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        return {
            "app": "BuSy",
            "version": 1,
            "created_at": timestamp,
            "updated_at": timestamp,
            "instance_id": os.getenv("BUSY_INSTANCE_ID", ""),
            "paths": {
                "database": str(self.database_path),
                "settings": str(self.settings_path),
                "storage": str(self.busy_root / "storage"),
                "logs": str(self.busy_root / "logs"),
                "backups": str(self.busy_root / "backups"),
                "tmp": str(self.busy_root / "tmp"),
            },
        }

    def _default_settings(self) -> dict[str, Any]:
        return {
            "app_name": "BuSy",
            "environment": os.getenv("BUSY_ENV", "development"),
            "storage_strategy": "local",
            "database": {
                "engine": "sqlite",
                "path": str(self.database_path),
            },
            "files": {
                "root": str(self.busy_root / "storage"),
                "categories": list(self.DEFAULT_STRUCTURE["storage"]),
            },
            "logs": {
                "root": str(self.busy_root / "logs"),
                "level": os.getenv("BUSY_LOG_LEVEL", "INFO"),
            },
        }


class Document:
    """
    Manejador simple para archivos dentro del runtime `.busy/`.
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
        return file_path

    def write_json(self, payload: dict[str, Any] | list[Any]) -> Path:
        file_path = self.retrieveDoc()
        file_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )
        return file_path

    def saveDoc(self, content: str) -> Path:
        return self.write(content, overwrite=True)

    def delete(self, *, missing_ok: bool = True) -> None:
        if self.path.exists():
            self.path.unlink()
            return
        if not missing_ok:
            raise FileNotFoundError(self.path)

    def _createDoc(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        return self.path


def bootstrap_busy_workspace(root_dir: str | Path | None = None) -> BusyPaths:
    paths = BusyPaths(root_dir=root_dir)
    paths.bootstrap()
    return paths
