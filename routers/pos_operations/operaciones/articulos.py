# articulos.py

from __future__ import annotations

import sqlite3
import uuid
import json
import shutil
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from databases.singleton import Database
from routers.authentication import User, current_user


router_articulos = APIRouter(prefix="/articulos")

ProductType = Literal["simple"]
InventoryTrackingMode = Literal["tracked", "untracked"]
ReservationPolicy = Literal["disabled", "allowed"]
StockStatus = Literal["in_stock", "out_of_stock", "backorder"]

READ_USER_TYPES = {1, 2, 3, 4}
WRITE_USER_TYPES = {1, 2, 3}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
DEFAULT_MAX_UPLOAD_MB = 25
IMAGE_CHUNK_SIZE = 1024 * 1024


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class ProductGeneral(ApiModel):
    name: str = Field(min_length=1)
    short_description: str = Field(alias="shortDescription", min_length=1)
    long_description: str = Field(default="", alias="longDescription")
    regular_price: float = Field(alias="regularPrice", ge=0)
    sale_price: float | None = Field(default=None, alias="salePrice", ge=0)

    @field_validator("name", "short_description", "long_description", mode="before")
    @classmethod
    def _trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ProductGeneralPatch(ApiModel):
    name: str | None = Field(default=None, min_length=1)
    short_description: str | None = Field(default=None, alias="shortDescription", min_length=1)
    long_description: str | None = Field(default=None, alias="longDescription")
    regular_price: float | None = Field(default=None, alias="regularPrice", ge=0)
    sale_price: float | None = Field(default=None, alias="salePrice", ge=0)

    @field_validator("name", "short_description", "long_description", mode="before")
    @classmethod
    def _trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ProductInventory(ApiModel):
    sku: str = Field(min_length=1)
    tracking_mode: InventoryTrackingMode = Field(default="tracked", alias="trackingMode")
    quantity: int | None = Field(default=1, ge=0)
    reservation_policy: ReservationPolicy | None = Field(default="disabled", alias="reservationPolicy")
    low_stock_threshold: int | None = Field(default=1, alias="lowStockThreshold", ge=0)
    stock_status: StockStatus = Field(default="in_stock", alias="stockStatus")

    @field_validator("sku", mode="before")
    @classmethod
    def _trim_sku(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _validate_tracking_state(self) -> "ProductInventory":
        if self.tracking_mode == "tracked" and self.quantity is None:
            raise ValueError("Tracked products require quantity")

        if self.tracking_mode == "untracked":
            invalid_fields = (
                self.quantity is not None
                or self.reservation_policy is not None
                or self.low_stock_threshold is not None
            )
            if invalid_fields:
                raise ValueError(
                    "Untracked products must not include quantity, reservationPolicy or lowStockThreshold"
                )

        return self


class ProductInventoryPatch(ApiModel):
    sku: str | None = Field(default=None, min_length=1)
    tracking_mode: InventoryTrackingMode | None = Field(default=None, alias="trackingMode")
    quantity: int | None = Field(default=None, ge=0)
    reservation_policy: ReservationPolicy | None = Field(default=None, alias="reservationPolicy")
    low_stock_threshold: int | None = Field(default=None, alias="lowStockThreshold", ge=0)
    stock_status: StockStatus | None = Field(default=None, alias="stockStatus")

    @field_validator("sku", mode="before")
    @classmethod
    def _trim_sku(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ProductAttributeInput(ApiModel):
    id: str | None = None
    name: str = ""
    values: list[str] = Field(default_factory=list)
    visible: bool = True

    @field_validator("name", mode="before")
    @classmethod
    def _trim_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("values", mode="before")
    @classmethod
    def _trim_values(cls, value: object) -> object:
        if isinstance(value, list):
            return [item.strip() for item in value if isinstance(item, str) and item.strip()]
        return value


class ProductAttributeOutput(ApiModel):
    id: str
    name: str
    values: list[str]
    visible: bool


class ProductImageInput(ApiModel):
    id: str | None = None
    url: str = Field(min_length=1)
    alt_text: str | None = Field(default=None, alias="altText")
    is_primary: bool = Field(default=False, alias="isPrimary")
    order: int = 0

    @field_validator("url", "alt_text", mode="before")
    @classmethod
    def _trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ProductImageOutput(ApiModel):
    id: str
    url: str
    alt_text: str | None = Field(default=None, alias="altText")
    is_primary: bool = Field(alias="isPrimary")
    order: int


class ProductMediaInput(ApiModel):
    images: list[ProductImageInput] = Field(default_factory=list)


class ProductMediaOutput(ApiModel):
    images: list[ProductImageOutput] = Field(default_factory=list)


class ProductMetadata(ApiModel):
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")
    is_active: bool = Field(alias="isActive")


class SimpleProductInput(ApiModel):
    id: str | None = None
    type: ProductType = "simple"
    general: ProductGeneral
    inventory: ProductInventory
    attributes: list[ProductAttributeInput] = Field(default_factory=list)
    media: ProductMediaInput = Field(default_factory=ProductMediaInput)
    metadata: dict[str, object] = Field(default_factory=dict)


class SimpleProductPatch(ApiModel):
    type: ProductType | None = None
    general: ProductGeneralPatch | None = None
    inventory: ProductInventoryPatch | None = None
    attributes: list[ProductAttributeInput] | None = None
    media: ProductMediaInput | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimpleProductOutput(ApiModel):
    id: str
    type: ProductType
    general: ProductGeneral
    inventory: ProductInventory
    attributes: list[ProductAttributeOutput] = Field(default_factory=list)
    media: ProductMediaOutput
    metadata: ProductMetadata


class ProductListResponse(ApiModel):
    items: list[SimpleProductOutput]
    page: int
    limit: int
    total: int


class ProductImageOrderInput(ApiModel):
    id: str = Field(min_length=1)
    is_primary: bool = Field(default=False, alias="isPrimary")


class ProductImagesOrderRequest(ApiModel):
    images: list[ProductImageOrderInput]


class AjustarExistenciasRequest(ApiModel):
    cantidad: int = Field(ge=0)
    motivo: str = Field(min_length=1)
    referencia: str | None = None

    @field_validator("motivo", "referencia", mode="before")
    @classmethod
    def _trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ClonarArticuloRequest(ApiModel):
    sku: str | None = Field(default=None, min_length=1)
    name: str | None = Field(default=None, min_length=1)

    @field_validator("sku", "name", mode="before")
    @classmethod
    def _trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def _price_to_cents(value: float) -> int:
    cents = (Decimal(str(value)) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(cents)


def _cents_to_price(value: int | None) -> float | None:
    return None if value is None else value / 100


def _bool_to_db(value: bool) -> int:
    return 1 if value else 0


def _db_to_bool(value: object) -> bool:
    return bool(int(value or 0))


def _require_read(user: User) -> None:
    if user.typeUser not in READ_USER_TYPES:
        raise HTTPException(status_code=403, detail="Not authorized to read articles")


def _require_write(user: User) -> None:
    if user.typeUser not in WRITE_USER_TYPES:
        raise HTTPException(status_code=403, detail="Not authorized to manage articles")


def _flush_archive(database: Database) -> None:
    flush = getattr(database, "_flush_archive", None)
    if callable(flush):
        flush()


def _image_url(image_id: str) -> str:
    return f"/articulos/imagenes/{image_id}"


def _product_images_dir(database: Database, product_id: str) -> Path:
    paths = getattr(database, "paths", None)
    if paths is None:
        raise HTTPException(status_code=500, detail="Image storage is not available")

    image_dir = paths.resolve_storage_path("images", f"products/{product_id}")
    image_dir.mkdir(parents=True, exist_ok=True)
    return image_dir


def _get_max_upload_bytes(database: Database) -> int:
    paths = getattr(database, "paths", None)
    if paths is None:
        return DEFAULT_MAX_UPLOAD_MB * 1024 * 1024

    try:
        payload = json.loads(paths.sysconfig_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_MAX_UPLOAD_MB * 1024 * 1024

    limits = payload.get("limits") if isinstance(payload, dict) else None
    raw_limit = limits.get("max_upload_mb") if isinstance(limits, dict) else DEFAULT_MAX_UPLOAD_MB
    try:
        max_upload_mb = int(raw_limit)
    except (TypeError, ValueError):
        max_upload_mb = DEFAULT_MAX_UPLOAD_MB

    return max(1, max_upload_mb) * 1024 * 1024


def _normalize_image_extension(filename: str | None, content_type: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    normalized_mime = (content_type or "").split(";")[0].strip().lower()

    if normalized_mime not in ALLOWED_IMAGE_MIME_TYPES:
        raise HTTPException(status_code=415, detail="Image type is not supported")

    if suffix and suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Image extension is not supported")

    expected_suffix = ALLOWED_IMAGE_MIME_TYPES[normalized_mime]
    if suffix and suffix not in {expected_suffix, ".jpeg" if expected_suffix == ".jpg" else expected_suffix}:
        raise HTTPException(status_code=415, detail="Image extension does not match image type")

    if suffix in ALLOWED_IMAGE_EXTENSIONS:
        return suffix

    return expected_suffix


def _find_product_image_file(database: Database, product_id: str, image_id: str) -> Path | None:
    image_dir = _product_images_dir(database, product_id)
    for extension in ALLOWED_IMAGE_EXTENSIONS:
        candidate = image_dir / f"{image_id}{extension}"
        if candidate.is_file():
            return candidate
    return None


def _delete_product_image_file(database: Database, product_id: str, image_id: str) -> None:
    image_path = _find_product_image_file(database, product_id, image_id)
    if image_path is not None:
        image_path.unlink(missing_ok=True)


async def _save_uploaded_product_image(
    database: Database,
    product_id: str,
    image_id: str,
    file: UploadFile,
) -> Path:
    extension = _normalize_image_extension(file.filename, file.content_type)
    image_path = _product_images_dir(database, product_id) / f"{image_id}{extension}"
    max_bytes = _get_max_upload_bytes(database)
    total_bytes = 0

    try:
        with image_path.open("wb") as handle:
            while True:
                chunk = await file.read(IMAGE_CHUNK_SIZE)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    handle.close()
                    image_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="Image exceeds the upload size limit")
                handle.write(chunk)
    finally:
        await file.close()

    if total_bytes == 0:
        image_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Image file is empty")

    return image_path


def _sku_exists(cursor: sqlite3.Cursor, sku: str, excluding_product_id: str | None = None) -> bool:
    params: list[object] = [sku]
    query = "SELECT id FROM products WHERE sku = ? AND is_active = 1"
    if excluding_product_id is not None:
        query += " AND id != ?"
        params.append(excluding_product_id)
    cursor.execute(query, tuple(params))
    return cursor.fetchone() is not None


def _ensure_unique_sku(cursor: sqlite3.Cursor, sku: str, excluding_product_id: str | None = None) -> None:
    if _sku_exists(cursor, sku, excluding_product_id):
        raise HTTPException(status_code=409, detail="SKU already exists")


def _ensure_product_active(cursor: sqlite3.Cursor, product_id: str) -> None:
    cursor.execute("SELECT id FROM products WHERE id = ? AND is_active = 1", (product_id,))
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Article not found")


def _count_product_images(cursor: sqlite3.Cursor, product_id: str) -> int:
    cursor.execute(
        "SELECT COUNT(*) AS total FROM product_images WHERE product_id = ?",
        (product_id,),
    )
    return int(cursor.fetchone()["total"])


def _fetch_product_image_row(
    cursor: sqlite3.Cursor,
    image_id: str,
    *,
    product_id: str | None = None,
) -> sqlite3.Row:
    params: list[object] = [image_id]
    query = "SELECT * FROM product_images WHERE id = ?"
    if product_id is not None:
        query += " AND product_id = ?"
        params.append(product_id)

    cursor.execute(query, tuple(params))
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return row


def _row_to_product_image(row: sqlite3.Row) -> ProductImageOutput:
    return ProductImageOutput(
        id=row["id"],
        url=row["url"],
        altText=row["alt_text"],
        isPrimary=_db_to_bool(row["is_primary"]),
        order=row["sort_order"],
    )


def _promote_first_product_image(cursor: sqlite3.Cursor, product_id: str) -> None:
    cursor.execute(
        """
        SELECT id FROM product_images
        WHERE product_id = ?
        ORDER BY sort_order, url
        LIMIT 1
        """,
        (product_id,),
    )
    row = cursor.fetchone()
    if row is not None:
        cursor.execute(
            "UPDATE product_images SET is_primary = 1 WHERE id = ?",
            (row["id"],),
        )


def _insert_product(
    cursor: sqlite3.Cursor,
    product: SimpleProductInput,
    *,
    product_id: str,
    created_at: str,
    updated_at: str,
) -> None:
    cursor.execute(
        """
        INSERT INTO products (
            id, type, name, short_description, long_description,
            regular_price_cents, sale_price_cents, sku, tracking_mode, quantity,
            reservation_policy, low_stock_threshold, stock_status,
            created_at, updated_at, is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            product_id,
            product.type,
            product.general.name,
            product.general.short_description,
            product.general.long_description,
            _price_to_cents(product.general.regular_price),
            _price_to_cents(product.general.sale_price) if product.general.sale_price is not None else None,
            product.inventory.sku,
            product.inventory.tracking_mode,
            product.inventory.quantity,
            product.inventory.reservation_policy,
            product.inventory.low_stock_threshold,
            product.inventory.stock_status,
            created_at,
            updated_at,
        ),
    )
    _replace_product_attributes(cursor, product_id, product.attributes)
    _replace_product_images(cursor, product_id, product.media.images)


def _replace_product(
    cursor: sqlite3.Cursor,
    product_id: str,
    product: SimpleProductInput,
    *,
    updated_at: str,
) -> None:
    cursor.execute(
        """
        UPDATE products
        SET
            type = ?,
            name = ?,
            short_description = ?,
            long_description = ?,
            regular_price_cents = ?,
            sale_price_cents = ?,
            sku = ?,
            tracking_mode = ?,
            quantity = ?,
            reservation_policy = ?,
            low_stock_threshold = ?,
            stock_status = ?,
            updated_at = ?
        WHERE id = ? AND is_active = 1
        """,
        (
            product.type,
            product.general.name,
            product.general.short_description,
            product.general.long_description,
            _price_to_cents(product.general.regular_price),
            _price_to_cents(product.general.sale_price) if product.general.sale_price is not None else None,
            product.inventory.sku,
            product.inventory.tracking_mode,
            product.inventory.quantity,
            product.inventory.reservation_policy,
            product.inventory.low_stock_threshold,
            product.inventory.stock_status,
            updated_at,
            product_id,
        ),
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Article not found")

    cursor.execute("DELETE FROM product_attributes WHERE product_id = ?", (product_id,))
    cursor.execute("DELETE FROM product_images WHERE product_id = ?", (product_id,))
    _replace_product_attributes(cursor, product_id, product.attributes)
    _replace_product_images(cursor, product_id, product.media.images)


def _replace_product_attributes(
    cursor: sqlite3.Cursor,
    product_id: str,
    attributes: list[ProductAttributeInput],
) -> None:
    for sort_order, attribute in enumerate(attributes):
        values = [value.strip() for value in attribute.values if value.strip()]
        name = attribute.name.strip()
        if not name and not values:
            continue

        attribute_id = _new_id()
        cursor.execute(
            """
            INSERT INTO product_attributes (id, product_id, name, visible, sort_order)
            VALUES (?, ?, ?, ?, ?)
            """,
            (attribute_id, product_id, name, _bool_to_db(attribute.visible), sort_order),
        )
        for value_order, value in enumerate(values):
            cursor.execute(
                """
                INSERT INTO product_attribute_values (id, attribute_id, value, sort_order)
                VALUES (?, ?, ?, ?)
                """,
                (_new_id(), attribute_id, value, value_order),
            )


def _replace_product_images(
    cursor: sqlite3.Cursor,
    product_id: str,
    images: list[ProductImageInput],
) -> None:
    primary_seen = False
    for sort_order, image in enumerate(images):
        is_primary = image.is_primary and not primary_seen
        primary_seen = primary_seen or is_primary
        cursor.execute(
            """
            INSERT INTO product_images (
                id, product_id, url, alt_text, is_primary, sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                _new_id(),
                product_id,
                image.url,
                image.alt_text,
                _bool_to_db(is_primary),
                image.order if image.order is not None else sort_order,
            ),
        )


def _fetch_product(cursor: sqlite3.Cursor, product_id: str, *, active_only: bool = True) -> SimpleProductOutput:
    query = "SELECT * FROM products WHERE id = ?"
    params: tuple[object, ...] = (product_id,)
    if active_only:
        query += " AND is_active = 1"

    cursor.execute(query, params)
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Article not found")

    return _row_to_product(cursor, row)


def _row_to_product(cursor: sqlite3.Cursor, row: sqlite3.Row) -> SimpleProductOutput:
    product_id = row["id"]
    cursor.execute(
        """
        SELECT * FROM product_attributes
        WHERE product_id = ?
        ORDER BY sort_order, name
        """,
        (product_id,),
    )
    attribute_rows = cursor.fetchall()
    attributes: list[ProductAttributeOutput] = []
    for attribute_row in attribute_rows:
        cursor.execute(
            """
            SELECT value FROM product_attribute_values
            WHERE attribute_id = ?
            ORDER BY sort_order, value
            """,
            (attribute_row["id"],),
        )
        values = [value_row["value"] for value_row in cursor.fetchall()]
        attributes.append(
            ProductAttributeOutput(
                id=attribute_row["id"],
                name=attribute_row["name"],
                values=values,
                visible=_db_to_bool(attribute_row["visible"]),
            )
        )

    cursor.execute(
        """
        SELECT * FROM product_images
        WHERE product_id = ?
        ORDER BY sort_order, url
        """,
        (product_id,),
    )
    images = [
        ProductImageOutput(
            id=image_row["id"],
            url=image_row["url"],
            altText=image_row["alt_text"],
            isPrimary=_db_to_bool(image_row["is_primary"]),
            order=image_row["sort_order"],
        )
        for image_row in cursor.fetchall()
    ]

    return SimpleProductOutput(
        id=product_id,
        type=row["type"],
        general=ProductGeneral(
            name=row["name"],
            shortDescription=row["short_description"],
            longDescription=row["long_description"],
            regularPrice=_cents_to_price(row["regular_price_cents"]),
            salePrice=_cents_to_price(row["sale_price_cents"]),
        ),
        inventory=ProductInventory(
            sku=row["sku"],
            trackingMode=row["tracking_mode"],
            quantity=row["quantity"],
            reservationPolicy=row["reservation_policy"],
            lowStockThreshold=row["low_stock_threshold"],
            stockStatus=row["stock_status"],
        ),
        attributes=attributes,
        media=ProductMediaOutput(images=images),
        metadata=ProductMetadata(
            createdAt=row["created_at"],
            updatedAt=row["updated_at"],
            isActive=_db_to_bool(row["is_active"]),
        ),
    )


def _merge_patch(existing: SimpleProductOutput, patch: SimpleProductPatch) -> SimpleProductInput:
    general = existing.general.model_copy()
    if patch.general is not None:
        general_updates = patch.general.model_dump(exclude_unset=True)
        general = general.model_copy(update=general_updates)

    inventory = existing.inventory.model_copy()
    if patch.inventory is not None:
        inventory_updates = patch.inventory.model_dump(exclude_unset=True)
        inventory = inventory.model_copy(update=inventory_updates)

    if inventory.tracking_mode == "untracked":
        inventory = inventory.model_copy(
            update={
                "quantity": None,
                "reservation_policy": None,
                "low_stock_threshold": None,
            }
        )
    elif inventory.quantity is None:
        inventory = inventory.model_copy(
            update={
                "quantity": 1,
                "reservation_policy": inventory.reservation_policy or "disabled",
                "low_stock_threshold": inventory.low_stock_threshold,
            }
        )

    attributes = (
        patch.attributes
        if patch.attributes is not None
        else [
            ProductAttributeInput(
                name=attribute.name,
                values=attribute.values,
                visible=attribute.visible,
            )
            for attribute in existing.attributes
        ]
    )
    media = (
        patch.media
        if patch.media is not None
        else ProductMediaInput(
            images=[
                ProductImageInput(
                    url=image.url,
                    altText=image.alt_text,
                    isPrimary=image.is_primary,
                    order=image.order,
                )
                for image in existing.media.images
            ]
        )
    )

    return SimpleProductInput(
        type=patch.type or existing.type,
        general=ProductGeneral.model_validate(general.model_dump()),
        inventory=ProductInventory.model_validate(inventory.model_dump()),
        attributes=attributes,
        media=media,
    )


def _generate_clone_sku(cursor: sqlite3.Cursor, original_sku: str) -> str:
    base_sku = f"{original_sku}-copy"
    candidate = base_sku
    suffix = 2
    while _sku_exists(cursor, candidate):
        candidate = f"{base_sku}-{suffix}"
        suffix += 1
    return candidate


def _copy_output_to_input(product: SimpleProductOutput, *, sku: str, name: str) -> SimpleProductInput:
    return SimpleProductInput(
        type=product.type,
        general=ProductGeneral(
            name=name,
            shortDescription=product.general.short_description,
            longDescription=product.general.long_description,
            regularPrice=product.general.regular_price,
            salePrice=product.general.sale_price,
        ),
        inventory=ProductInventory(
            sku=sku,
            trackingMode=product.inventory.tracking_mode,
            quantity=product.inventory.quantity,
            reservationPolicy=product.inventory.reservation_policy,
            lowStockThreshold=product.inventory.low_stock_threshold,
            stockStatus=product.inventory.stock_status,
        ),
        attributes=[
            ProductAttributeInput(
                name=attribute.name,
                values=attribute.values,
                visible=attribute.visible,
            )
            for attribute in product.attributes
        ],
        media=ProductMediaInput(
            images=[
                ProductImageInput(
                    url=image.url,
                    altText=image.alt_text,
                    isPrimary=image.is_primary,
                    order=image.order,
                )
                for image in product.media.images
            ]
        ),
    )


def _copy_product_image_files_and_rows(
    cursor: sqlite3.Cursor,
    database: Database,
    *,
    source_product_id: str,
    target_product_id: str,
) -> None:
    cursor.execute(
        """
        SELECT * FROM product_images
        WHERE product_id = ?
        ORDER BY sort_order, url
        """,
        (source_product_id,),
    )
    rows = cursor.fetchall()

    for sort_order, row in enumerate(rows):
        source_image_id = row["id"]
        target_image_id = _new_id()
        target_url = row["url"]
        source_file = _find_product_image_file(database, source_product_id, source_image_id)

        if source_file is not None:
            target_file = _product_images_dir(database, target_product_id) / f"{target_image_id}{source_file.suffix}"
            shutil.copy2(source_file, target_file)
            target_url = _image_url(target_image_id)

        cursor.execute(
            """
            INSERT INTO product_images (
                id, product_id, url, alt_text, is_primary, sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                target_image_id,
                target_product_id,
                target_url,
                row["alt_text"],
                row["is_primary"],
                sort_order,
            ),
        )


@router_articulos.get("/ison")
async def ison():
    return {
        "message": "Yes, I'm on from '/articulos'",
    }


@router_articulos.get("/imagenes/{image_id}")
async def obtener_imagen_articulo(
    image_id: str,
    user: User = Depends(current_user),
):
    _require_read(user)
    database = Database()
    cursor = database.connection.cursor()

    try:
        image_row = _fetch_product_image_row(cursor, image_id)
        image_path = _find_product_image_file(database, image_row["product_id"], image_id)
        if image_path is None:
            raise HTTPException(status_code=404, detail="Image file not found")

        media_type = next(
            (
                mime_type
                for mime_type, extension in ALLOWED_IMAGE_MIME_TYPES.items()
                if extension == image_path.suffix.lower()
            ),
            "application/octet-stream",
        )
        return FileResponse(image_path, media_type=media_type)
    finally:
        cursor.close()


@router_articulos.post(
    "/{product_id}/imagenes",
    response_model=ProductImageOutput,
    status_code=status.HTTP_201_CREATED,
)
async def subir_imagen_articulo(
    product_id: str,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
):
    _require_write(user)
    database = Database()
    cursor = database.connection.cursor()
    image_id = _new_id()
    image_path: Path | None = None

    try:
        _ensure_product_active(cursor, product_id)
        image_path = await _save_uploaded_product_image(database, product_id, image_id, file)
        is_primary = _count_product_images(cursor, product_id) == 0

        with database.connection:
            cursor.execute(
                """
                INSERT INTO product_images (
                    id, product_id, url, alt_text, is_primary, sort_order
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    image_id,
                    product_id,
                    _image_url(image_id),
                    file.filename,
                    _bool_to_db(is_primary),
                    _count_product_images(cursor, product_id),
                ),
            )
        _flush_archive(database)
        return _row_to_product_image(_fetch_product_image_row(cursor, image_id, product_id=product_id))
    except Exception:
        if image_path is not None:
            image_path.unlink(missing_ok=True)
        raise
    finally:
        cursor.close()


@router_articulos.patch("/{product_id}/imagenes", response_model=SimpleProductOutput)
async def ordenar_imagenes_articulo(
    product_id: str,
    payload: ProductImagesOrderRequest,
    user: User = Depends(current_user),
):
    _require_write(user)
    database = Database()
    cursor = database.connection.cursor()

    try:
        with database.connection:
            _ensure_product_active(cursor, product_id)
            requested_ids = [image.id for image in payload.images]
            if len(requested_ids) != len(set(requested_ids)):
                raise HTTPException(status_code=400, detail="Image order contains duplicates")

            cursor.execute(
                "SELECT id FROM product_images WHERE product_id = ?",
                (product_id,),
            )
            existing_ids = {row["id"] for row in cursor.fetchall()}
            if set(requested_ids) != existing_ids:
                raise HTTPException(status_code=400, detail="Image order must include every product image")

            primary_ids = [image.id for image in payload.images if image.is_primary]
            primary_id = primary_ids[0] if primary_ids else (requested_ids[0] if requested_ids else None)

            cursor.execute(
                "UPDATE product_images SET is_primary = 0 WHERE product_id = ?",
                (product_id,),
            )
            for sort_order, image in enumerate(payload.images):
                cursor.execute(
                    """
                    UPDATE product_images
                    SET sort_order = ?, is_primary = ?
                    WHERE product_id = ? AND id = ?
                    """,
                    (
                        sort_order,
                        _bool_to_db(image.id == primary_id),
                        product_id,
                        image.id,
                    ),
                )
        _flush_archive(database)
        return _fetch_product(cursor, product_id)
    finally:
        cursor.close()


@router_articulos.delete("/{product_id}/imagenes/{image_id}", response_model=SimpleProductOutput)
async def eliminar_imagen_articulo(
    product_id: str,
    image_id: str,
    user: User = Depends(current_user),
):
    _require_write(user)
    database = Database()
    cursor = database.connection.cursor()

    try:
        with database.connection:
            _ensure_product_active(cursor, product_id)
            image_row = _fetch_product_image_row(cursor, image_id, product_id=product_id)
            was_primary = _db_to_bool(image_row["is_primary"])
            cursor.execute(
                "DELETE FROM product_images WHERE product_id = ? AND id = ?",
                (product_id, image_id),
            )
            if was_primary:
                _promote_first_product_image(cursor, product_id)
        _delete_product_image_file(database, product_id, image_id)
        _flush_archive(database)
        return _fetch_product(cursor, product_id)
    finally:
        cursor.close()


@router_articulos.post(
    "/agregar",
    response_model=SimpleProductOutput,
    status_code=status.HTTP_201_CREATED,
)
async def agregar_articulo(
    articulo: SimpleProductInput,
    user: User = Depends(current_user),
):
    _require_write(user)
    database = Database()
    cursor = database.connection.cursor()
    product_id = _new_id()
    now = _now_iso()

    try:
        with database.connection:
            _ensure_unique_sku(cursor, articulo.inventory.sku)
            _insert_product(cursor, articulo, product_id=product_id, created_at=now, updated_at=now)
        _flush_archive(database)
        return _fetch_product(cursor, product_id)
    except HTTPException:
        raise
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Article could not be created") from exc
    finally:
        cursor.close()


@router_articulos.patch("/{product_id}/editar", response_model=SimpleProductOutput)
async def editar_articulo(
    product_id: str,
    articulo: SimpleProductPatch,
    user: User = Depends(current_user),
):
    _require_write(user)
    database = Database()
    cursor = database.connection.cursor()
    now = _now_iso()

    try:
        with database.connection:
            existing = _fetch_product(cursor, product_id)
            product = _merge_patch(existing, articulo)
            _ensure_unique_sku(cursor, product.inventory.sku, excluding_product_id=product_id)
            _replace_product(cursor, product_id, product, updated_at=now)
        _flush_archive(database)
        return _fetch_product(cursor, product_id)
    except HTTPException:
        raise
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_context=False)) from exc
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Article could not be updated") from exc
    finally:
        cursor.close()


@router_articulos.get("/recargar", response_model=ProductListResponse)
async def recargar_articulos(
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(current_user),
):
    _require_read(user)
    database = Database()
    cursor = database.connection.cursor()
    offset = (page - 1) * limit
    search_term = (q or "").strip()
    params: list[object] = []
    where_clause = "WHERE is_active = 1"

    if search_term:
        where_clause += """
            AND (
                sku LIKE ? COLLATE NOCASE
                OR name LIKE ? COLLATE NOCASE
                OR short_description LIKE ? COLLATE NOCASE
                OR long_description LIKE ? COLLATE NOCASE
            )
        """
        pattern = f"%{search_term}%"
        params.extend([pattern, pattern, pattern, pattern])

    try:
        cursor.execute(f"SELECT COUNT(*) AS total FROM products {where_clause}", tuple(params))
        total = int(cursor.fetchone()["total"])

        cursor.execute(
            f"""
            SELECT * FROM products
            {where_clause}
            ORDER BY updated_at DESC, name COLLATE NOCASE
            LIMIT ? OFFSET ?
            """,
            tuple(params + [limit, offset]),
        )
        items = [_row_to_product(cursor, row) for row in cursor.fetchall()]
        return ProductListResponse(items=items, page=page, limit=limit, total=total)
    finally:
        cursor.close()


@router_articulos.delete("/{product_id}/eliminar")
async def eliminar_articulo(
    product_id: str,
    user: User = Depends(current_user),
):
    _require_write(user)
    database = Database()
    cursor = database.connection.cursor()

    try:
        with database.connection:
            cursor.execute(
                """
                UPDATE products
                SET is_active = 0, updated_at = ?
                WHERE id = ? AND is_active = 1
                """,
                (_now_iso(), product_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Article not found")
        _flush_archive(database)
        return {"message": "Article deleted successfully", "id": product_id}
    finally:
        cursor.close()


@router_articulos.post("/{product_id}/ajustar", response_model=SimpleProductOutput)
async def ajustar_existencias(
    product_id: str,
    ajuste: AjustarExistenciasRequest,
    user: User = Depends(current_user),
):
    _require_write(user)
    database = Database()
    cursor = database.connection.cursor()
    now = _now_iso()

    try:
        with database.connection:
            cursor.execute(
                "SELECT * FROM products WHERE id = ? AND is_active = 1",
                (product_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Article not found")
            if row["tracking_mode"] != "tracked":
                raise HTTPException(status_code=400, detail="Article does not track inventory quantity")

            previous_quantity = int(row["quantity"] or 0)
            next_stock_status = "out_of_stock" if ajuste.cantidad == 0 else "in_stock"

            cursor.execute(
                """
                UPDATE products
                SET quantity = ?, stock_status = ?, updated_at = ?
                WHERE id = ? AND is_active = 1
                """,
                (ajuste.cantidad, next_stock_status, now, product_id),
            )
            cursor.execute(
                """
                INSERT INTO inventory_adjustments (
                    id, product_id, previous_quantity, new_quantity,
                    reason, reference, user_id, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _new_id(),
                    product_id,
                    previous_quantity,
                    ajuste.cantidad,
                    ajuste.motivo,
                    ajuste.referencia,
                    user.id,
                    now,
                ),
            )
        _flush_archive(database)
        return _fetch_product(cursor, product_id)
    finally:
        cursor.close()


@router_articulos.post(
    "/{product_id}/clonar",
    response_model=SimpleProductOutput,
    status_code=status.HTTP_201_CREATED,
)
async def clonar_articulo(
    product_id: str,
    clon: ClonarArticuloRequest | None = Body(default=None),
    user: User = Depends(current_user),
):
    _require_write(user)
    database = Database()
    cursor = database.connection.cursor()
    now = _now_iso()
    new_product_id = _new_id()
    clone_options = clon or ClonarArticuloRequest()

    try:
        with database.connection:
            original = _fetch_product(cursor, product_id)
            sku = clone_options.sku or _generate_clone_sku(cursor, original.inventory.sku)
            name = clone_options.name or f"{original.general.name} (clon)"
            _ensure_unique_sku(cursor, sku)
            product = _copy_output_to_input(original, sku=sku, name=name)
            product = product.model_copy(update={"media": ProductMediaInput(images=[])})
            _insert_product(cursor, product, product_id=new_product_id, created_at=now, updated_at=now)
            _copy_product_image_files_and_rows(
                cursor,
                database,
                source_product_id=product_id,
                target_product_id=new_product_id,
            )
        _flush_archive(database)
        return _fetch_product(cursor, new_product_id)
    except HTTPException:
        raise
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Article could not be cloned") from exc
    finally:
        cursor.close()
