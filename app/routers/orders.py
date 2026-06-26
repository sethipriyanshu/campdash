from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import ledger, mailer, ratelimit
from app.config import get_settings
from app.db import get_db
from app.deps import get_bank
from app.models import MenuItem, Order, OrderStatus, TxType
from app.schemas import OrderRequest, OrderResponse, to_sb
from bank import ShadyBankClient, ShadyBankError

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=OrderResponse)
async def place_order(
    body: OrderRequest,
    db: AsyncSession = Depends(get_db),
    bank: ShadyBankClient = Depends(get_bank),
) -> OrderResponse:
    """Checkout: charge ShadyBucks (card+OTP) into the house, record the order, email the food photo.
    Idempotent on `idempotency_key` so a double-tap never double-charges."""
    settings = get_settings()

    # Idempotency fast-path.
    existing = (await db.execute(
        select(Order).where(Order.idempotency_key == body.idempotency_key)
    )).scalar_one_or_none()
    if existing is not None:
        return _resp(existing)

    # Abuse guard (per card number) — a failed card+OTP shouldn't be hammered.
    if not ratelimit.allow(f"order:{body.pan}", settings.order_max_attempts, settings.order_window_seconds):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too many attempts — wait a bit")

    item = await db.get(MenuItem, body.item_id)
    if not item or not item.available:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "item not available")
    subtotal_cents = item.price_cents * body.qty
    fee_cents = subtotal_cents * settings.delivery_fee_bps // 10000  # 30% delivery fee on top
    total_cents = subtotal_cents + fee_cents

    # 1. Charge: log in with the customer's card+OTP, credit the house the total.
    try:
        cust_token = await bank.login(pan=body.pan, otp=body.otp)
    except ShadyBankError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "ShadyBucks login failed (check card / OTP)")
    bank_desc = f"cd:order:{body.idempotency_key}"
    try:
        await bank.credit(cust_token, Decimal(total_cents) / 100, pan=settings.house_pan, description=bank_desc)
    except ShadyBankError:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "payment declined (insufficient ShadyBucks?)")

    # 2. Record the order + ledger sale (charge already happened — must persist).
    acct_id = None
    try:
        acct_id = int((await bank.balance(cust_token))["account"])
    except ShadyBankError:
        pass
    external = await ledger.get_system_account(db, "EXTERNAL")
    house = await ledger.get_system_account(db, "HOUSE")
    tx = await ledger.post_tx(db, TxType.SALE, [(external.id, house.id, total_cents)],
                              meta={"idempotency_key": body.idempotency_key})
    order = Order(
        item_id=item.id, item_name=item.name, qty=body.qty, total_cents=total_cents,
        email=body.email, address=body.address, phone=body.phone, shadybank_account_id=acct_id,
        status=OrderStatus.PAID, bank_desc=bank_desc, idempotency_key=body.idempotency_key, tx_id=tx.id,
    )
    db.add(order)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        existing = (await db.execute(
            select(Order).where(Order.idempotency_key == body.idempotency_key)
        )).scalar_one()
        return _resp(existing)
    await db.commit()

    # 3. "Deliver" — email the food photo. Best-effort: a failure marks EMAIL_FAILED (retryable),
    #    never reverses the paid order.
    emailed = await _send_photo(db, order, item)
    return _resp(order, emailed=emailed)


async def _send_photo(db: AsyncSession, order: Order, item: MenuItem) -> bool:
    from datetime import datetime, timezone
    try:
        await mailer.send_order_email(
            to=order.email,
            subject="Your CampDash has arrived 🍔",
            html=mailer.order_email_html(item.name, order.qty, to_sb(order.total_cents).__str__(), order.address),
            photo_path=item.photo_path,
            photo_name=f"{item.name.lower().replace(' ', '-')}.jpg",
        )
        order.status = OrderStatus.PAID
        order.email_sent_at = datetime.now(timezone.utc)
        order.email_error = None
        await db.commit()
        return True
    except Exception as e:  # noqa: BLE001
        order.status = OrderStatus.EMAIL_FAILED
        order.email_error = str(e)[:255]
        await db.commit()
        return False


def _resp(o: Order, emailed: bool | None = None) -> OrderResponse:
    return OrderResponse(
        order_id=o.id, item_name=o.item_name, qty=o.qty, total_cents=o.total_cents,
        total=to_sb(o.total_cents), email=o.email, status=o.status.value,
        emailed=(o.email_sent_at is not None) if emailed is None else emailed,
    )
