from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class AccountType(str, enum.Enum):
    EXTERNAL = "EXTERNAL"
    HOUSE = "HOUSE"


class TxType(str, enum.Enum):
    SALE = "SALE"  # external -> house (a food order)


class OrderStatus(str, enum.Enum):
    PAID = "PAID"                  # charged + email sent
    EMAIL_FAILED = "EMAIL_FAILED"  # charged but the photo email didn't send (retryable)


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120))
    blurb: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_cents: Mapped[int] = mapped_column(BigInteger)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)  # /media/<file>
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LedgerAccount(Base):
    __tablename__ = "ledger_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    type: Mapped[AccountType] = mapped_column(Enum(AccountType, name="account_type"), index=True)
    label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LedgerTx(Base):
    __tablename__ = "ledger_tx"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    type: Mapped[TxType] = mapped_column(Enum(TxType, name="tx_type"), index=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="tx", cascade="all, delete-orphan")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (CheckConstraint("amount_cents > 0", name="amount_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tx_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ledger_tx.id"), index=True)
    from_account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ledger_accounts.id"), index=True)
    to_account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ledger_accounts.id"), index=True)
    amount_cents: Mapped[int] = mapped_column(BigInteger)

    tx: Mapped["LedgerTx"] = relationship(back_populates="entries")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("menu_items.id"), index=True)
    item_name: Mapped[str] = mapped_column(String(120))   # snapshot at purchase time
    qty: Mapped[int] = mapped_column(Integer, default=1)
    total_cents: Mapped[int] = mapped_column(BigInteger)
    email: Mapped[str] = mapped_column(String(255), index=True)
    address: Mapped[str] = mapped_column(Text)            # display-only / satirical
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)  # optional, display-only
    shadybank_account_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"), default=OrderStatus.PAID, index=True
    )
    bank_desc: Mapped[str] = mapped_column(String(120))
    idempotency_key: Mapped[str] = mapped_column(String(80), unique=True)
    tx_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ledger_tx.id"), nullable=True)
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
