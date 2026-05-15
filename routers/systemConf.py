from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from databases.singleton import Database
from routers.authentication import User, current_user


router_systemconf = APIRouter(prefix="/systemconf")

ADMIN_USER_TYPES = {1, 2}
COMPANY_PROFILE_ID = 1

EDITABLE_COMPANY_FIELDS = (
    "legal_name",
    "trade_name",
    "rfc",
    "tax_regime",
    "email",
    "phone",
    "website",
    "street",
    "exterior_number",
    "interior_number",
    "neighborhood",
    "city",
    "state",
    "country",
    "postal_code",
    "logo_path",
    "currency",
    "timezone",
    "locale",
)

NON_EMPTY_DEFAULTS = {
    "country": "México",
    "currency": "MXN",
    "timezone": "America/Mexico_City",
    "locale": "es-MX",
}


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class CompanyProfileInput(ApiModel):
    legal_name: str = ""
    trade_name: str = ""
    rfc: str = ""
    tax_regime: str = ""
    email: str = ""
    phone: str = ""
    website: str = ""
    street: str = ""
    exterior_number: str = ""
    interior_number: str = ""
    neighborhood: str = ""
    city: str = ""
    state: str = ""
    country: str = NON_EMPTY_DEFAULTS["country"]
    postal_code: str = ""
    logo_path: str = ""
    currency: str = NON_EMPTY_DEFAULTS["currency"]
    timezone: str = NON_EMPTY_DEFAULTS["timezone"]
    locale: str = NON_EMPTY_DEFAULTS["locale"]

    @field_validator("*", mode="before")
    @classmethod
    def _trim_text(cls, value: object) -> object:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def _apply_required_defaults(self) -> "CompanyProfileInput":
        for field_name, default_value in NON_EMPTY_DEFAULTS.items():
            if not getattr(self, field_name):
                setattr(self, field_name, default_value)
        return self


class CompanyProfileOutput(CompanyProfileInput):
    id: int
    created_at: str
    updated_at: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_admin(user: User) -> None:
    if user.typeUser not in ADMIN_USER_TYPES:
        raise HTTPException(status_code=403, detail="Not authorized to manage system configuration")


def _flush_archive(database: Database) -> None:
    flush = getattr(database, "_flush_archive", None)
    if callable(flush):
        flush()


def _ensure_company_profile(cursor: sqlite3.Cursor) -> None:
    now = _now_iso()
    cursor.execute(
        """
        INSERT OR IGNORE INTO company_profile (
            id,
            legal_name,
            trade_name,
            rfc,
            country,
            currency,
            timezone,
            locale,
            created_at,
            updated_at
        )
        VALUES (?, '', 'Business System Demo', '', ?, ?, ?, ?, ?, ?)
        """,
        (
            COMPANY_PROFILE_ID,
            NON_EMPTY_DEFAULTS["country"],
            NON_EMPTY_DEFAULTS["currency"],
            NON_EMPTY_DEFAULTS["timezone"],
            NON_EMPTY_DEFAULTS["locale"],
            now,
            now,
        ),
    )


def _fetch_company_profile(cursor: sqlite3.Cursor) -> CompanyProfileOutput:
    cursor.execute(
        "SELECT * FROM company_profile WHERE id = ?",
        (COMPANY_PROFILE_ID,),
    )
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Company profile not found")
    return CompanyProfileOutput(**dict(row))


@router_systemconf.get("/ison")
async def ison():
    return {"message": "Yes, I'm on from '/systemconf'"}


@router_systemconf.get("/company-profile", response_model=CompanyProfileOutput)
async def get_company_profile(user: User = Depends(current_user)):
    _require_admin(user)
    database = Database()
    cursor = database.connection.cursor()

    try:
        with database.connection:
            _ensure_company_profile(cursor)
        _flush_archive(database)
        return _fetch_company_profile(cursor)
    finally:
        cursor.close()


@router_systemconf.put("/company-profile", response_model=CompanyProfileOutput)
async def update_company_profile(
    profile: CompanyProfileInput,
    user: User = Depends(current_user),
):
    _require_admin(user)
    database = Database()
    cursor = database.connection.cursor()
    now = _now_iso()

    try:
        with database.connection:
            _ensure_company_profile(cursor)
            values = [getattr(profile, field_name) for field_name in EDITABLE_COMPANY_FIELDS]
            values.extend([now, COMPANY_PROFILE_ID])
            cursor.execute(
                f"""
                UPDATE company_profile
                SET
                    {", ".join(f"{field_name} = ?" for field_name in EDITABLE_COMPANY_FIELDS)},
                    updated_at = ?
                WHERE id = ?
                """,
                tuple(values),
            )
        _flush_archive(database)
        return _fetch_company_profile(cursor)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Company profile could not be updated") from exc
    finally:
        cursor.close()
