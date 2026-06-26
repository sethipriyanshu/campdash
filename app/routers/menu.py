from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.models import MenuItem
from app.schemas import MenuItemOut, to_sb

router = APIRouter(prefix="/api/menu", tags=["menu"])
config_router = APIRouter(prefix="/api/config", tags=["config"])


@config_router.get("")
async def public_config() -> dict:
    """Public knobs the UI needs to mirror the server (e.g. the delivery fee shown at checkout)."""
    s = get_settings()
    return {"delivery_fee_bps": s.delivery_fee_bps}


def _out(m: MenuItem) -> MenuItemOut:
    return MenuItemOut(id=m.id, name=m.name, blurb=m.blurb, price_cents=m.price_cents,
                       price=to_sb(m.price_cents), photo_path=m.photo_path, available=m.available)


@router.get("", response_model=list[MenuItemOut])
async def list_menu(db: AsyncSession = Depends(get_db)) -> list[MenuItemOut]:
    """Public — anyone can browse the menu."""
    rows = (await db.execute(
        select(MenuItem).where(MenuItem.available == True).order_by(MenuItem.sort, MenuItem.name)  # noqa: E712
    )).scalars().all()
    return [_out(m) for m in rows]


@router.get("/{item_id}", response_model=MenuItemOut)
async def get_item(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> MenuItemOut:
    m = await db.get(MenuItem, item_id)
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "item not found")
    return _out(m)
