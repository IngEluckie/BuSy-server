from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

from utilities.security.passwords import hash_password
from utilities.handleDocument.document import CURRENT_DATABASE_SCHEMA_VERSION

if TYPE_CHECKING:
    from utilities.handleDocument.document import BusyPaths


# IMPORTANT:
# Schema changes must be implemented as ordered migrations. Do not modify
# SCHEMA_STATEMENTS as the runtime DB contract without also bumping
# CURRENT_DATABASE_SCHEMA_VERSION in utilities.handleDocument.document.
SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS user_type (
        id INTEGER NOT NULL UNIQUE,
        type TEXT,
        PRIMARY KEY(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS info_db (
        id INTEGER NOT NULL UNIQUE,
        info VARCHAR,
        PRIMARY KEY(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER NOT NULL UNIQUE,
        user_type INTEGER NOT NULL,
        username VARCHAR NOT NULL,
        fullname TEXT NOT NULL,
        cellphone INTEGER,
        email TEXT,
        birthday DATETIME,
        rfc VARCHAR,
        password VARCHAR NOT NULL,
        PRIMARY KEY(id),
        FOREIGN KEY(user_type) REFERENCES user_type(id)
            ON UPDATE NO ACTION
            ON DELETE NO ACTION
    )
    """,
)

USER_TYPE_SEED: tuple[tuple[int, str], ...] = (
    (1, "superadmin"),
    (2, "admin"),
    (3, "manager"),
    (4, "vendor"),
    (5, "customer"),
)

SUPERADMIN_SEED: dict[str, object] = {
    "id": 1,
    "user_type": 1,
    "username": "admin",
    "fullname": "System Super Administrator",
    "cellphone": 1111111111,
    "email": "admin@busy.local",
    "birthday": None,
    "rfc": "XAXX010101000",
    "password": "1",
}


def migrate_database(
    connection: sqlite3.Connection,
    paths: "BusyPaths | None" = None,
) -> bool:
    # SQLite PRAGMA user_version is the persisted schema version. New schema
    # versions must be migrated in order before the app uses the database.
    current_version = get_database_user_version(connection)

    if current_version > CURRENT_DATABASE_SCHEMA_VERSION:
        raise RuntimeError(
            "La base de datos requiere una version mas nueva de BuSy."
        )

    if current_version == CURRENT_DATABASE_SCHEMA_VERSION:
        return False

    cursor = connection.cursor()
    try:
        while current_version < CURRENT_DATABASE_SCHEMA_VERSION:
            if current_version == 0:
                _migrate_database_0_to_1(cursor)
                current_version = 1
                continue

            raise RuntimeError(
                f"No existe migracion para base de datos version {current_version}."
            )

        cursor.execute(f"PRAGMA user_version = {CURRENT_DATABASE_SCHEMA_VERSION}")
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def database_needs_migration(connection: sqlite3.Connection) -> bool:
    current_version = get_database_user_version(connection)
    return current_version < CURRENT_DATABASE_SCHEMA_VERSION


def get_database_user_version(connection: sqlite3.Connection) -> int:
    cursor = connection.cursor()
    try:
        cursor.execute("PRAGMA user_version")
        row = cursor.fetchone()
        return int(row[0] if row is not None else 0)
    finally:
        cursor.close()


def initialize_database(connection: sqlite3.Connection, db_path: str | Path) -> None:
    migrated = migrate_database(connection)
    if migrated:
        print(f"Base de datos inicializada o migrada en: {db_path}")


def needs_database_initialization(connection: sqlite3.Connection) -> bool:
    return database_needs_migration(connection)


def _migrate_database_0_to_1(cursor: sqlite3.Cursor) -> None:
    for statement in SCHEMA_STATEMENTS:
        cursor.execute(statement)

    cursor.executemany(
        "INSERT OR IGNORE INTO user_type (id, type) VALUES (?, ?)",
        USER_TYPE_SEED,
    )

    cursor.execute(
        """
        INSERT OR IGNORE INTO users (
            id, user_type, username, fullname, cellphone, email, birthday, rfc, password
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            SUPERADMIN_SEED["id"],
            SUPERADMIN_SEED["user_type"],
            SUPERADMIN_SEED["username"],
            SUPERADMIN_SEED["fullname"],
            SUPERADMIN_SEED["cellphone"],
            SUPERADMIN_SEED["email"],
            SUPERADMIN_SEED["birthday"],
            SUPERADMIN_SEED["rfc"],
            hash_password(str(SUPERADMIN_SEED["password"])),
        ),
    )
