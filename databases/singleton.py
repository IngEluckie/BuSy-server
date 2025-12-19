"""
Singleton para acceso a SQLite.

Nota: una misma conexión SQLite no es segura para compartir entre hilos de forma
general. Este diseño mantiene 1 instancia global (configuración) y crea 1
conexión por hilo (thread-local).
"""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


_instance_lock = threading.Lock()
_instance: Optional["DatabaseManager"] = None


@dataclass(frozen=True, slots=True)
class SQLiteConfig:
    db_path: Path
    timeout: float = 30.0


class DatabaseManager:
    def __init__(self, config: SQLiteConfig) -> None:
        self._config = config
        self._local = threading.local()

    @property
    def config(self) -> SQLiteConfig:
        return self._config

    def connection(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            return conn

        conn = sqlite3.connect(self._config.db_path, timeout=self._config.timeout)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        self._local.conn = conn
        return conn

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            return
        try:
            conn.close()
        finally:
            self._local.conn = None

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        return self.connection().execute(sql, params)

    def executescript(self, sql_script: str) -> None:
        self.connection().executescript(sql_script)


def init_sqlite(db_path: str | Path, *, timeout: float = 30.0) -> DatabaseManager:
    """
    Inicializa el singleton. Si ya está inicializado con otra ruta, falla.
    """
    global _instance

    path = Path(db_path)
    with _instance_lock:
        if _instance is None:
            _instance = DatabaseManager(SQLiteConfig(db_path=path, timeout=timeout))
            return _instance

        if _instance.config.db_path != path:
            raise RuntimeError(
                f"SQLiteDB ya inicializado con {_instance.config.db_path}, no con {path}"
            )
        return _instance


def get_sqlite() -> DatabaseManager:
    if _instance is None:
        raise RuntimeError("SQLiteDB no inicializado. Llama init_sqlite(...) primero.")
    return _instance
