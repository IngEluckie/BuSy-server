import json
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

    def _payload(self, sku: str = "SKU-1", *, include_images: bool = True) -> dict:
        payload = {
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
                "images": []
            },
        }

        if include_images:
            payload["media"]["images"] = [
                {
                    "url": "/storage/images/vestido.jpg",
                    "altText": "Vestido azul",
                    "isPrimary": True,
                    "order": 0,
                }
            ]

        return payload

    def _create_product(self, sku: str = "SKU-1") -> dict:
        response = self.client.post("/articulos/agregar", json=self._payload(sku, include_images=False))
        self.assertEqual(response.status_code, 201)
        return response.json()

    def _upload_image(
        self,
        product_id: str,
        *,
        filename: str = "vestido.png",
        content: bytes = b"image-bytes",
        content_type: str = "image/png",
    ) -> dict:
        response = self.client.post(
            f"/articulos/{product_id}/imagenes",
            files={"file": (filename, content, content_type)},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def _product_image_files(self, product_id: str) -> list[Path]:
        image_dir = BusyPaths(root_dir=self.root).resolve_storage_path(
            "images",
            f"products/{product_id}",
        )
        if not image_dir.exists():
            return []
        return [path for path in image_dir.iterdir() if path.is_file()]

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

    def test_upload_and_serve_product_image_from_busy_storage(self) -> None:
        product = self._create_product()
        image = self._upload_image(product["id"], content=b"png-content")

        self.assertEqual(image["url"], f"/articulos/imagenes/{image['id']}")
        self.assertTrue(image["isPrimary"])
        self.assertEqual(image["order"], 0)

        database = Database(root_dir=self.root)
        image_rows = database.fetch_query("SELECT * FROM product_images WHERE id = ?", (image["id"],))
        self.assertIsNotNone(image_rows)
        self.assertEqual(len(image_rows), 1)

        image_files = self._product_image_files(product["id"])
        self.assertEqual(len(image_files), 1)
        self.assertEqual(image_files[0].name, f"{image['id']}.png")

        response = self.client.get(image["url"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"png-content")
        self.assertEqual(response.headers["content-type"], "image/png")

    def test_upload_rejects_unsupported_image_type(self) -> None:
        product = self._create_product()
        response = self.client.post(
            f"/articulos/{product['id']}/imagenes",
            files={"file": ("bad.gif", b"gif-content", "image/gif")},
        )

        self.assertEqual(response.status_code, 415)
        self.assertEqual(self._product_image_files(product["id"]), [])

    def test_upload_rejects_mismatched_extension_and_type(self) -> None:
        product = self._create_product()
        response = self.client.post(
            f"/articulos/{product['id']}/imagenes",
            files={"file": ("mismatch.png", b"jpg-content", "image/jpeg")},
        )

        self.assertEqual(response.status_code, 415)
        self.assertEqual(self._product_image_files(product["id"]), [])

    def test_upload_rejects_images_over_configured_limit(self) -> None:
        product = self._create_product()
        paths = BusyPaths(root_dir=self.root)
        sysconfig = json.loads(paths.sysconfig_path.read_text(encoding="utf-8"))
        sysconfig["limits"]["max_upload_mb"] = 1
        paths.sysconfig_path.write_text(json.dumps(sysconfig), encoding="utf-8")

        response = self.client.post(
            f"/articulos/{product['id']}/imagenes",
            files={"file": ("large.png", b"x" * ((1024 * 1024) + 1), "image/png")},
        )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(self._product_image_files(product["id"]), [])

    def test_delete_image_removes_file_and_promotes_next_primary(self) -> None:
        product = self._create_product()
        first_image = self._upload_image(product["id"], filename="first.jpg", content=b"first", content_type="image/jpeg")
        second_image = self._upload_image(product["id"], filename="second.webp", content=b"second", content_type="image/webp")

        response = self.client.delete(f"/articulos/{product['id']}/imagenes/{first_image['id']}")
        self.assertEqual(response.status_code, 200)
        images = response.json()["media"]["images"]

        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["id"], second_image["id"])
        self.assertTrue(images[0]["isPrimary"])
        self.assertEqual([path.name for path in self._product_image_files(product["id"])], [f"{second_image['id']}.webp"])

    def test_reorder_product_images_sets_order_and_primary(self) -> None:
        product = self._create_product()
        first_image = self._upload_image(product["id"], filename="first.png")
        second_image = self._upload_image(product["id"], filename="second.png")

        response = self.client.patch(
            f"/articulos/{product['id']}/imagenes",
            json={
                "images": [
                    {"id": second_image["id"], "isPrimary": True},
                    {"id": first_image["id"], "isPrimary": False},
                ]
            },
        )
        self.assertEqual(response.status_code, 200)

        images = response.json()["media"]["images"]
        self.assertEqual([image["id"] for image in images], [second_image["id"], first_image["id"]])
        self.assertEqual([image["order"] for image in images], [0, 1])
        self.assertTrue(images[0]["isPrimary"])
        self.assertFalse(images[1]["isPrimary"])

    def test_edit_product_preserves_existing_image_ids_and_urls(self) -> None:
        product = self._create_product()
        first_image = self._upload_image(product["id"], filename="first.png", content=b"first")
        second_image = self._upload_image(product["id"], filename="second.png", content=b"second")

        edit_response = self.client.patch(
            f"/articulos/{product['id']}/editar",
            json={
                "general": {
                    "name": "Vestido azul editado",
                }
            },
        )
        self.assertEqual(edit_response.status_code, 200)

        images = edit_response.json()["media"]["images"]
        self.assertEqual([image["id"] for image in images], [first_image["id"], second_image["id"]])
        self.assertEqual([image["url"] for image in images], [first_image["url"], second_image["url"]])

        first_image_response = self.client.get(first_image["url"])
        self.assertEqual(first_image_response.status_code, 200)
        self.assertEqual(first_image_response.content, b"first")

        delete_response = self.client.delete(f"/articulos/{product['id']}/imagenes/{first_image['id']}")
        self.assertEqual(delete_response.status_code, 200)
        remaining_images = delete_response.json()["media"]["images"]
        self.assertEqual([image["id"] for image in remaining_images], [second_image["id"]])
        self.assertTrue(remaining_images[0]["isPrimary"])

    def test_clone_copies_product_image_files(self) -> None:
        product = self._create_product()
        original_image = self._upload_image(product["id"], filename="vestido.jpeg", content=b"clone-source", content_type="image/jpeg")

        response = self.client.post(f"/articulos/{product['id']}/clonar")
        self.assertEqual(response.status_code, 201)
        clone = response.json()
        clone_image = clone["media"]["images"][0]

        self.assertNotEqual(clone["id"], product["id"])
        self.assertNotEqual(clone_image["id"], original_image["id"])
        self.assertEqual(clone_image["altText"], "vestido.jpeg")
        self.assertTrue(clone_image["isPrimary"])
        self.assertEqual(clone_image["url"], f"/articulos/imagenes/{clone_image['id']}")

        original_files = self._product_image_files(product["id"])
        clone_files = self._product_image_files(clone["id"])
        self.assertEqual(len(original_files), 1)
        self.assertEqual(len(clone_files), 1)
        self.assertEqual(original_files[0].read_bytes(), clone_files[0].read_bytes())
        self.assertNotEqual(original_files[0], clone_files[0])

    def test_delete_article_keeps_physical_images(self) -> None:
        product = self._create_product()
        image = self._upload_image(product["id"], content=b"keep-me")
        image_files = self._product_image_files(product["id"])
        self.assertEqual(len(image_files), 1)

        response = self.client.delete(f"/articulos/{product['id']}/eliminar")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(image_files[0].exists())

        image_response = self.client.get(image["url"])
        self.assertEqual(image_response.status_code, 200)
        self.assertEqual(image_response.content, b"keep-me")


if __name__ == "__main__":
    unittest.main()
