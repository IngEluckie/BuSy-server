import os
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from databases.singleton import Database
from utilities.handleDocument.document import BusyPaths, Document, bootstrap_busy_workspace


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

    def test_bootstrap_creates_busy_zip_with_default_structure(self) -> None:
        paths = bootstrap_busy_workspace(root_dir=self.root)

        self.assertTrue(paths.archive_path.exists())
        self.assertFalse((self.root / ".busy").exists())

        with zipfile.ZipFile(paths.archive_path, "r") as archive:
            names = set(archive.namelist())

        self.assertIn("meta/manifest.json", names)
        self.assertIn("config/settings.json", names)
        self.assertIn("config/app.env.example", names)
        self.assertIn("db/.keep", names)
        self.assertIn("logs/.keep", names)
        self.assertIn("backups/.keep", names)
        self.assertIn("tmp/.keep", names)
        self.assertIn("storage/documents/.keep", names)

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

    def test_legacy_busy_directory_is_ignored_without_archive(self) -> None:
        legacy_document = self.root / ".busy" / "storage" / "documents" / "legacy.txt"
        legacy_document.parent.mkdir(parents=True, exist_ok=True)
        legacy_document.write_text("legacy-content", encoding="utf-8")

        paths = bootstrap_busy_workspace(root_dir=self.root)

        with zipfile.ZipFile(paths.archive_path, "r") as archive:
            names = set(archive.namelist())

        self.assertNotIn("storage/documents/legacy.txt", names)
        self.assertFalse(paths.resolve_storage_path("documents", "legacy.txt").exists())


if __name__ == "__main__":
    unittest.main()
