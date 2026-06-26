from __future__ import annotations

import re
import uuid

from pydantic import BaseModel, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def to_sb(cents: int) -> float:
    return round(cents / 100, 2)


class MenuItemOut(BaseModel):
    id: uuid.UUID
    name: str
    blurb: str | None
    price_cents: int
    price: float
    photo_path: str | None
    available: bool


class OrderRequest(BaseModel):
    item_id: uuid.UUID
    qty: int = Field(1, ge=1, le=20)
    email: str = Field(..., max_length=255)
    address: str = Field(..., min_length=1, max_length=500)  # display-only / satirical
    phone: str | None = Field(None, max_length=40)           # optional, display-only / satirical
    pan: str = Field(..., description="ShadyBucks card number")
    otp: str = Field(..., description="One-time passcode")
    idempotency_key: str = Field(..., min_length=8, max_length=80)

    @field_validator("email")
    @classmethod
    def _email_ok(cls, v: str) -> str:
        if not _EMAIL_RE.match(v.strip()):
            raise ValueError("enter a valid email")
        return v.strip()


class OrderResponse(BaseModel):
    order_id: uuid.UUID
    item_name: str
    qty: int
    total_cents: int
    total: float
    email: str
    status: str
    emailed: bool
