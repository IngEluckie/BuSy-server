# articulos.py

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
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


@router_articulos.get("/ison")
async def ison():
    return {
        "message": "Yes, I'm on from '/articulos'",
    }


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
            _insert_product(cursor, product, product_id=new_product_id, created_at=now, updated_at=now)
        _flush_archive(database)
        return _fetch_product(cursor, new_product_id)
    except HTTPException:
        raise
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Article could not be cloned") from exc
    finally:
        cursor.close()
