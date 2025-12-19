"""
Utilidades para crear/inicializar una base de datos SQLite.

Uso rápido:
    from databases.createdb import create_sqlite_database
    create_sqlite_database("databases/busy.sqlite3")
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Sequence


def create_sqlite_database(
    db_path: str | Path,
    *,
    schema: str | Sequence[str] | None = None,
    overwrite: bool = False,
) -> Path:
    """
    Crea un archivo de base de datos SQLite y opcionalmente ejecuta un esquema.

    - Si `overwrite=False` y el archivo ya existe, lanza `FileExistsError`.
    - `schema` puede ser un string con SQL (se ejecuta con executescript) o
      una secuencia de sentencias (se ejecutan una por una).
    """

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists() and not overwrite:
        raise FileExistsError(f"SQLite DB ya existe: {path}")

    if overwrite and path.exists():
        path.unlink()

    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")

        if schema:
            _apply_schema(conn, schema)

        conn.commit()
    finally:
        conn.close()

    return path


def _apply_schema(conn: sqlite3.Connection, schema: str | Sequence[str]) -> None:
    if isinstance(schema, str):
        conn.executescript(schema)
        return

    for stmt in schema:
        if stmt.strip():
            conn.execute(stmt)
