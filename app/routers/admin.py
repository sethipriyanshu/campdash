from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import require_admin
from app.models import MenuItem, Order, OrderStatus
from app.routers.orders import _send_photo
from app.schemas import to_sb

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/check")
async def check() -> dict:
    return {"ok": True}


@router.get("/orders")
async def list_orders(db: AsyncSession = Depends(get_db)) -> dict:
    rows = (await db.execute(select(Order).order_by(Order.created_at.desc()))).scalars().all()
    total = sum(o.total_cents for o in rows)
    return {
        "sales_total_cents": total,
        "sales_total": to_sb(total),
        "count": len(rows),
        "orders": [{
            "id": str(o.id), "item": o.item_name, "qty": o.qty, "total": to_sb(o.total_cents),
            "email": o.email, "address": o.address, "phone": o.phone, "status": o.status.value,
            "email_error": o.email_error, "created_at": o.created_at.isoformat(),
        } for o in rows],
    }


@router.post("/orders/{order_id}/resend-email")
async def resend_email(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found")
    item = await db.get(MenuItem, order.item_id)
    emailed = await _send_photo(db, order, item)
    return {"id": str(order.id), "emailed": emailed, "status": order.status.value, "error": order.email_error}
