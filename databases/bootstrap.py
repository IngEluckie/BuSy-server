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

            if current_version == 1:
                _migrate_database_1_to_2(cursor)
                current_version = 2
                continue

            if current_version == 2:
                _migrate_database_2_to_3(cursor)
                current_version = 3
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


def _migrate_database_1_to_2(cursor: sqlite3.Cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'simple'
                CHECK (type IN ('simple')),
            name TEXT NOT NULL,
            short_description TEXT NOT NULL,
            long_description TEXT NOT NULL DEFAULT '',
            regular_price_cents INTEGER NOT NULL
                CHECK (regular_price_cents >= 0),
            sale_price_cents INTEGER
                CHECK (sale_price_cents IS NULL OR sale_price_cents >= 0),
            sku TEXT NOT NULL,
            tracking_mode TEXT NOT NULL DEFAULT 'tracked'
                CHECK (tracking_mode IN ('tracked', 'untracked')),
            quantity INTEGER
                CHECK (quantity IS NULL OR quantity >= 0),
            reservation_policy TEXT
                CHECK (reservation_policy IN ('disabled', 'allowed')),
            low_stock_threshold INTEGER
                CHECK (low_stock_threshold IS NULL OR low_stock_threshold >= 0),
            stock_status TEXT NOT NULL DEFAULT 'in_stock'
                CHECK (stock_status IN ('in_stock', 'out_of_stock', 'backorder')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
                CHECK (is_active IN (0, 1)),
            PRIMARY KEY(id),
            CHECK (
                (
                    tracking_mode = 'tracked'
                    AND quantity IS NOT NULL
                )
                OR (
                    tracking_mode = 'untracked'
                    AND quantity IS NULL
                    AND reservation_policy IS NULL
                    AND low_stock_threshold IS NULL
                )
            )
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS product_attributes (
            id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            name TEXT NOT NULL,
            visible INTEGER NOT NULL DEFAULT 1
                CHECK (visible IN (0, 1)),
            sort_order INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
                ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS product_attribute_values (
            id TEXT NOT NULL,
            attribute_id TEXT NOT NULL,
            value TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(id),
            FOREIGN KEY(attribute_id) REFERENCES product_attributes(id)
                ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS product_images (
            id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            url TEXT NOT NULL,
            alt_text TEXT,
            is_primary INTEGER NOT NULL DEFAULT 0
                CHECK (is_primary IN (0, 1)),
            sort_order INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
                ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_adjustments (
            id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            previous_quantity INTEGER NOT NULL
                CHECK (previous_quantity >= 0),
            new_quantity INTEGER NOT NULL
                CHECK (new_quantity >= 0),
            reason TEXT NOT NULL,
            reference TEXT,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
                ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id)
                ON DELETE NO ACTION
        )
        """
    )

    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_products_active_sku
        ON products(sku)
        WHERE is_active = 1
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_name ON products(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_active ON products(is_active)")
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_product_attributes_product_id
        ON product_attributes(product_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_product_images_product_id
        ON product_images(product_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_inventory_adjustments_product_id
        ON inventory_adjustments(product_id)
        """
    )


def _migrate_database_2_to_3(cursor: sqlite3.Cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS company_profile (
            id INTEGER NOT NULL DEFAULT 1
                CHECK (id = 1),
            legal_name TEXT NOT NULL DEFAULT '',
            trade_name TEXT NOT NULL DEFAULT '',
            rfc TEXT NOT NULL DEFAULT '',
            tax_regime TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            website TEXT NOT NULL DEFAULT '',
            street TEXT NOT NULL DEFAULT '',
            exterior_number TEXT NOT NULL DEFAULT '',
            interior_number TEXT NOT NULL DEFAULT '',
            neighborhood TEXT NOT NULL DEFAULT '',
            city TEXT NOT NULL DEFAULT '',
            state TEXT NOT NULL DEFAULT '',
            country TEXT NOT NULL DEFAULT 'México',
            postal_code TEXT NOT NULL DEFAULT '',
            logo_path TEXT NOT NULL DEFAULT '',
            currency TEXT NOT NULL DEFAULT 'MXN',
            timezone TEXT NOT NULL DEFAULT 'America/Mexico_City',
            locale TEXT NOT NULL DEFAULT 'es-MX',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(id)
        )
        """
    )

    cursor.execute(
        """
        INSERT OR IGNORE INTO company_profile (
            id,
            legal_name,
            trade_name,
            rfc,
            created_at,
            updated_at
        )
        VALUES (
            1,
            '',
            'Business System Demo',
            '',
            datetime('now'),
            datetime('now')
        )
        """
    )
