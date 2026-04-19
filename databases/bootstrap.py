from __future__ import annotations

import sqlite3
from pathlib import Path

from utilities.security.passwords import hash_password


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


def initialize_database(connection: sqlite3.Connection, db_path: str | Path) -> None:
    cursor = connection.cursor()
    try:
        for statement in SCHEMA_STATEMENTS:
            cursor.execute(statement)

        cursor.executemany(
            "INSERT OR IGNORE INTO user_type (id, type) VALUES (?, ?)",
            USER_TYPE_SEED,
        )

        cursor.execute(
            """
            INSERT INTO users (
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
        connection.commit()
        print(f"Base de datos inicializada desde cero en: {db_path}")
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def needs_database_initialization(connection: sqlite3.Connection) -> bool:
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name IN ('user_type', 'info_db', 'users')
            """
        )
        tables = {row[0] for row in cursor.fetchall()}
        return tables != {"user_type", "info_db", "users"}
    finally:
        cursor.close()
