import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from databases.singleton import Database
from utilities.handleDocument.document import (
    CURRENT_DATABASE_SCHEMA_VERSION,
    BusyPaths,
)

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from routers.pos_operations.operaciones import articulos
except ModuleNotFoundError:
    FastAPI = None
    TestClient = None
    articulos = None


class ArticleMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.previous_runtime_dir = os.environ.get("BUSY_RUNTIME_DIR")
        self.previous_archive_path = os.environ.get("BUSY_ARCHIVE_PATH")
        os.environ["BUSY_RUNTIME_DIR"] = str(self.root / "runtime")
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

    def test_article_tables_are_created_by_database_migration(self) -> None:
        database = Database(root_dir=self.root)
        version = database.connection.execute("PRAGMA user_version").fetchone()[0]
        rows = database.fetch_query(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name IN (
                'products',
                'product_attributes',
                'product_attribute_values',
                'product_images',
                'inventory_adjustments'
              )
            """
        )

        self.assertEqual(version, CURRENT_DATABASE_SCHEMA_VERSION)
        self.assertIsNotNone(rows)
        self.assertEqual(len(rows), 5)


@unittest.skipIf(TestClient is None, "FastAPI is not installed")
class ArticleRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.previous_runtime_dir = os.environ.get("BUSY_RUNTIME_DIR")
        self.previous_archive_path = os.environ.get("BUSY_ARCHIVE_PATH")
        os.environ["BUSY_RUNTIME_DIR"] = str(self.root / "runtime")
        os.environ.pop("BUSY_ARCHIVE_PATH", None)

        self.original_database = articulos.Database
        articulos.Database = lambda: Database(root_dir=self.root)

        self.app = FastAPI()
        self.app.include_router(articulos.router_articulos)
        self.app.dependency_overrides[articulos.current_user] = lambda: articulos.User(
            id=1,
            username="admin",
            fullname="Admin",
            birthday=None,
            rfc=None,
            cellphone=None,
            email=None,
            typeUser=1,
        )
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        articulos.Database = self.original_database

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

    def _payload(self, sku: str = "SKU-1") -> dict:
        return {
            "type": "simple",
            "general": {
                "name": "Vestido azul",
                "shortDescription": "Vestido infantil",
                "longDescription": "Vestido infantil de algodon",
                "regularPrice": 249.9,
                "salePrice": None,
            },
            "inventory": {
                "sku": sku,
                "trackingMode": "tracked",
                "quantity": 3,
                "reservationPolicy": "disabled",
                "lowStockThreshold": 1,
                "stockStatus": "in_stock",
            },
            "attributes": [
                {
                    "name": "Talla",
                    "values": ["2", "4"],
                    "visible": True,
                }
            ],
            "media": {
                "images": [
                    {
                        "url": "/storage/images/vestido.jpg",
                        "altText": "Vestido azul",
                        "isPrimary": True,
                        "order": 0,
                    }
                ]
            },
        }

    def test_create_list_adjust_clone_and_delete_article(self) -> None:
        create_response = self.client.post("/articulos/agregar", json=self._payload())
        self.assertEqual(create_response.status_code, 201)
        product = create_response.json()
        product_id = product["id"]
        self.assertEqual(product["inventory"]["sku"], "SKU-1")
        self.assertEqual(product["general"]["regularPrice"], 249.9)
        self.assertTrue(product["attributes"][0]["id"])

        duplicate_response = self.client.post("/articulos/agregar", json=self._payload())
        self.assertEqual(duplicate_response.status_code, 409)

        list_response = self.client.get("/articulos/recargar", params={"q": "vestido"})
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["total"], 1)

        adjust_response = self.client.post(
            f"/articulos/{product_id}/ajustar",
            json={"cantidad": 0, "motivo": "Conteo fisico"},
        )
        self.assertEqual(adjust_response.status_code, 200)
        self.assertEqual(adjust_response.json()["inventory"]["quantity"], 0)
        self.assertEqual(adjust_response.json()["inventory"]["stockStatus"], "out_of_stock")

        database = Database(root_dir=self.root)
        adjustment_rows = database.fetch_query("SELECT * FROM inventory_adjustments")
        self.assertIsNotNone(adjustment_rows)
        self.assertEqual(len(adjustment_rows), 1)

        clone_response = self.client.post(f"/articulos/{product_id}/clonar")
        self.assertEqual(clone_response.status_code, 201)
        self.assertNotEqual(clone_response.json()["id"], product_id)
        self.assertEqual(clone_response.json()["inventory"]["sku"], "SKU-1-copy")

        delete_response = self.client.delete(f"/articulos/{product_id}/eliminar")
        self.assertEqual(delete_response.status_code, 200)

        final_list_response = self.client.get("/articulos/recargar")
        self.assertEqual(final_list_response.status_code, 200)
        self.assertEqual(final_list_response.json()["total"], 1)


if __name__ == "__main__":
    unittest.main()
