"""Minimal double-entry ledger for reconciliation. EXTERNAL + HOUSE are singletons."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AccountType, LedgerAccount, LedgerEntry, LedgerTx, TxType


async def get_system_account(db: AsyncSession, label: str) -> LedgerAccount:
    existing = (
        await db.execute(select(LedgerAccount).where(LedgerAccount.label == label))
    ).scalar_one_or_none()
    if existing:
        return existing
    acct = LedgerAccount(type=AccountType[label], label=label)
    db.add(acct)
    await db.flush()
    return acct


async def post_tx(
    db: AsyncSession, tx_type: TxType,
    entries: list[tuple[uuid.UUID, uuid.UUID, int]], meta: dict | None = None,
) -> LedgerTx:
    tx = LedgerTx(type=tx_type, meta=meta)
    db.add(tx)
    await db.flush()
    for from_id, to_id, amount in entries:
        db.add(LedgerEntry(tx_id=tx.id, from_account_id=from_id, to_account_id=to_id, amount_cents=amount))
    await db.flush()
    return tx


async def balance_cents(db: AsyncSession, account_id: uuid.UUID) -> int:
    credits = (await db.execute(
        select(func.coalesce(func.sum(LedgerEntry.amount_cents), 0)).where(LedgerEntry.to_account_id == account_id)
    )).scalar_one()
    debits = (await db.execute(
        select(func.coalesce(func.sum(LedgerEntry.amount_cents), 0)).where(LedgerEntry.from_account_id == account_id)
    )).scalar_one()
    return int(credits) - int(debits)
