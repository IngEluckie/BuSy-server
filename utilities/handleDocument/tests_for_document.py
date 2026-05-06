import json
import os
import sqlite3
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from databases.bootstrap import SCHEMA_STATEMENTS
from databases.singleton import Database
from utilities.handleDocument.document import (
    CURRENT_BUSY_FORMAT_VERSION,
    CURRENT_DATABASE_SCHEMA_VERSION,
    BusyPaths,
    Document,
    bootstrap_busy_workspace,
)


class BusyArchivePersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.runtime_dir = self.root / "runtime"
        self.previous_runtime_dir = os.environ.get("BUSY_RUNTIME_DIR")
        self.previous_archive_path = os.environ.get("BUSY_ARCHIVE_PATH")
        os.environ["BUSY_RUNTIME_DIR"] = str(self.runtime_dir)
        os.environ.pop("BUSY_ARCHIVE_PATH", None)

    def tearDown(self) -> None:
        for instance in list(Database._instances.values()):
            instance.close_connection()

        try:
            BusyPaths(root_dir=self.root).cleanup()
        except Exception:
            pass

        if self.previous_runtime_dir is None:
            os.environ.pop("BUSY_RUNTIME_DIR", None)
        else:
            os.environ["BUSY_RUNTIME_DIR"] = self.previous_runtime_dir

        if self.previous_archive_path is None:
            os.environ.pop("BUSY_ARCHIVE_PATH", None)
        else:
            os.environ["BUSY_ARCHIVE_PATH"] = self.previous_archive_path

        self.temp_dir.cleanup()

    def _write_archive(
        self,
        entries: dict[str, str | bytes],
        *,
        archive_path: Path | None = None,
        files: dict[str, Path] | None = None,
    ) -> Path:
        archive_path = archive_path or self.root / ".busy"
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in entries.items():
                archive.writestr(name, content)
            for name, file_path in (files or {}).items():
                archive.write(file_path, arcname=name)

        return archive_path

    def _read_archive_json(self, name: str, *, archive_path: Path | None = None) -> dict:
        archive_path = archive_path or self.root / ".busy"
        with zipfile.ZipFile(archive_path, "r") as archive:
            return json.loads(archive.read(name).decode("utf-8"))

    def _legacy_manifest(self) -> dict:
        return {
            "app": "BuSy",
            "version": 1,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "instance_id": "",
            "paths": {
                "database": "/legacy/db/main.sqlite3",
                "settings": "/legacy/config/settings.json",
                "storage": "/legacy/storage",
                "logs": "/legacy/logs",
                "backups": "/legacy/backups",
                "tmp": "/legacy/tmp",
            },
        }

    def test_bootstrap_creates_busy_archive_with_default_structure(self) -> None:
        paths = bootstrap_busy_workspace(root_dir=self.root)

        self.assertTrue(paths.archive_path.exists())
        self.assertEqual(paths.archive_path.name, ".busy")
        self.assertTrue(paths.archive_path.is_file())

        with zipfile.ZipFile(paths.archive_path, "r") as archive:
            names = set(archive.namelist())

        self.assertIn("meta/manifest.json", names)
        self.assertIn("config/settings.json", names)
        self.assertIn("config/sysconfig.json", names)
        self.assertIn("config/app.env.example", names)
        self.assertIn("db/.keep", names)
        self.assertIn("logs/.keep", names)
        self.assertIn("backups/.keep", names)
        self.assertIn("tmp/.keep", names)
        self.assertIn("storage/documents/.keep", names)

        manifest = self._read_archive_json("meta/manifest.json")
        self.assertEqual(manifest["busy_format_version"], CURRENT_BUSY_FORMAT_VERSION)
        self.assertEqual(
            manifest["database_schema_version"],
            CURRENT_DATABASE_SCHEMA_VERSION,
        )

        sysconfig = self._read_archive_json("config/sysconfig.json")
        self.assertEqual(sysconfig["system"]["name"], "BuSy")
        self.assertTrue(sysconfig["modules"]["sysconf"])

    def test_legacy_busy_archive_is_migrated_and_preserves_files(self) -> None:
        self._write_archive(
            {
                "meta/manifest.json": json.dumps(self._legacy_manifest()),
                "config/settings.json": json.dumps(
                    {
                        "app_name": "Custom BuSy",
                        "database": {
                            "engine": "sqlite",
                            "path": "/old/runtime/db.sqlite3",
                        },
                        "files": {
                            "categories": ["custom"],
                        },
                    }
                ),
                "storage/documents/legacy.txt": "legacy data",
            }
        )

        paths = bootstrap_busy_workspace(root_dir=self.root)

        with zipfile.ZipFile(paths.archive_path, "r") as archive:
            names = set(archive.namelist())
            legacy_text = archive.read("storage/documents/legacy.txt").decode("utf-8")

        manifest = self._read_archive_json("meta/manifest.json")
        settings = self._read_archive_json("config/settings.json")

        self.assertEqual(legacy_text, "legacy data")
        self.assertIn("config/app.env.example", names)
        self.assertEqual(manifest["busy_format_version"], CURRENT_BUSY_FORMAT_VERSION)
        self.assertEqual(settings["app_name"], "Custom BuSy")
        self.assertEqual(settings["database"]["engine"], "sqlite")
        self.assertEqual(
            settings["database"]["path"],
            str(paths.runtime_root / "db" / "main.sqlite3"),
        )
        self.assertEqual(settings["files"]["root"], str(paths.runtime_root / "storage"))
        self.assertIn("custom", settings["files"]["categories"])
        self.assertIn("documents", settings["files"]["categories"])

    def test_busy_format_one_archive_gets_sysconfig_in_config(self) -> None:
        manifest = self._legacy_manifest()
        manifest["busy_format_version"] = 1
        manifest["database_schema_version"] = CURRENT_DATABASE_SCHEMA_VERSION
        self._write_archive(
            {
                "meta/manifest.json": json.dumps(manifest),
                "config/settings.json": "{}",
                "storage/documents/legacy.txt": "legacy data",
            }
        )

        bootstrap_busy_workspace(root_dir=self.root)

        manifest = self._read_archive_json("meta/manifest.json")
        sysconfig = self._read_archive_json("config/sysconfig.json")

        self.assertEqual(manifest["busy_format_version"], CURRENT_BUSY_FORMAT_VERSION)
        self.assertEqual(sysconfig["system"]["name"], "BuSy")
        self.assertEqual(sysconfig["system"]["locale"], "es-MX")
        self.assertTrue(sysconfig["modules"]["sysconf"])

    def test_busy_migration_failure_restores_backup_and_fails(self) -> None:
        self._write_archive(
            {
                "meta/manifest.json": json.dumps(self._legacy_manifest()),
                "config/settings.json": "{}",
                "storage/documents/legacy.txt": "legacy data",
            }
        )

        with patch.object(
            BusyPaths,
            "_migrate_busy_format_0_to_1_locked",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                bootstrap_busy_workspace(root_dir=self.root)

        backups = list(self.root.glob(".busy.backup-*"))
        manifest = self._read_archive_json("meta/manifest.json")

        self.assertTrue(backups)
        self.assertNotIn("busy_format_version", manifest)

    def test_custom_archive_path_creates_backup_next_to_custom_archive(self) -> None:
        custom_archive = self.root / ".busy.custom"
        os.environ["BUSY_ARCHIVE_PATH"] = str(custom_archive)
        self._write_archive(
            {
                "meta/manifest.json": json.dumps(self._legacy_manifest()),
                "config/settings.json": "{}",
            },
            archive_path=custom_archive,
        )

        bootstrap_busy_workspace(root_dir=self.root)

        backups = list(self.root.glob(".busy.custom.backup-*"))
        self.assertTrue(backups)

    def test_document_write_persists_across_runtime_cleanup(self) -> None:
        document = Document("note.txt", root_dir=self.root)
        document.write("persisted text")

        BusyPaths(root_dir=self.root).cleanup()

        restored = Document("note.txt", root_dir=self.root)
        self.assertEqual(restored.read(), "persisted text")

    def test_database_changes_are_archived_and_restore_after_cleanup(self) -> None:
        database = Database(root_dir=self.root)
        database.execute_query(
            "CREATE TABLE IF NOT EXISTS archive_test (id INTEGER PRIMARY KEY, value TEXT)"
        )
        database.execute_query(
            "INSERT INTO archive_test (value) VALUES (?)",
            ("ok",),
        )
        database.close_connection()

        BusyPaths(root_dir=self.root).cleanup()

        restored_database = Database(root_dir=self.root)
        rows = restored_database.fetch_query("SELECT value FROM archive_test")

        self.assertIsNotNone(rows)
        self.assertTrue(any(row["value"] == "ok" for row in rows or []))

    def test_empty_database_is_created_via_migration(self) -> None:
        database = Database(root_dir=self.root)

        version = database.connection.execute("PRAGMA user_version").fetchone()[0]
        rows = database.fetch_query("SELECT username FROM users WHERE id = 1")

        self.assertEqual(version, CURRENT_DATABASE_SCHEMA_VERSION)
        self.assertIsNotNone(rows)
        self.assertTrue(any(row["username"] == "admin" for row in rows or []))

    def test_legacy_database_user_version_zero_is_marked_current_without_data_loss(self) -> None:
        database_path = self.root / "legacy.sqlite3"
        with sqlite3.connect(database_path) as connection:
            cursor = connection.cursor()
            for statement in SCHEMA_STATEMENTS:
                cursor.execute(statement)
            cursor.execute(
                """
                INSERT INTO user_type (id, type) VALUES (?, ?)
                """,
                (9, "legacy"),
            )
            cursor.execute(
                """
                INSERT INTO users (
                    id, user_type, username, fullname, cellphone, email, birthday, rfc, password
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    2,
                    9,
                    "legacy-user",
                    "Legacy User",
                    None,
                    "legacy@example.com",
                    None,
                    None,
                    "legacy-password",
                ),
            )
            cursor.execute("PRAGMA user_version = 0")
            connection.commit()

        manifest = self._legacy_manifest()
        manifest["busy_format_version"] = CURRENT_BUSY_FORMAT_VERSION
        manifest["database_schema_version"] = 0
        self._write_archive(
            {
                "meta/manifest.json": json.dumps(manifest),
                "config/settings.json": "{}",
            },
            files={"db/main.sqlite3": database_path},
        )

        database = Database(root_dir=self.root)
        version = database.connection.execute("PRAGMA user_version").fetchone()[0]
        rows = database.fetch_query("SELECT username FROM users WHERE id = 2")
        manifest = self._read_archive_json("meta/manifest.json")

        self.assertEqual(version, CURRENT_DATABASE_SCHEMA_VERSION)
        self.assertIsNotNone(rows)
        self.assertTrue(any(row["username"] == "legacy-user" for row in rows or []))
        self.assertEqual(
            manifest["database_schema_version"],
            CURRENT_DATABASE_SCHEMA_VERSION,
        )

    def test_custom_archive_path_without_zip_extension_is_respected(self) -> None:
        os.environ["BUSY_ARCHIVE_PATH"] = str(self.root / ".busy.custom")

        paths = bootstrap_busy_workspace(root_dir=self.root)

        self.assertEqual(paths.archive_path.name, ".busy.custom")
        self.assertTrue(paths.archive_path.exists())
        self.assertFalse((self.root / ".busy.custom.zip").exists())


if __name__ == "__main__":
    unittest.main()
