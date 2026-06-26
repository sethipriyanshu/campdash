#!/usr/bin/env python3
"""CampDash Phase 0: prove the rail — charge a card to the house + send the photo email.

  customer --credit(price)--> house     (PUSH; customer's token, no extra step)
  then: photo email is sent (dev mode logs it if no Resend key)

Run the local shadybank first and top up the test card.
    ./.venv/bin/python scripts/test_roundtrip.py
"""
from __future__ import annotations

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

import pyotp

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import ledger, mailer  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import Base, get_engine, get_sessionmaker  # noqa: E402
from app.models import TxType  # noqa: E402
from bank import ShadyBankClient  # noqa: E402

CUST_PAN, CUST_TOTP = "8997000000000001", "JBSWY3DPEHPK3PXP"
PRICE = Decimal("12.00")  # a 12 SB burger

PASS, FAIL = "\033[32mPASS\033[0m", "\033[31mFAIL\033[0m"
_fail = 0


def check(label, got, want):
    global _fail
    ok = got == want
    _fail += 0 if ok else 1
    print(f"  [{PASS if ok else FAIL}] {label}: got {got!r}, want {want!r}")


async def bal(bank, pan, pin):
    return Decimal(str((await bank.balance(await bank.login(pan=pan, pin=pin)))["balance"]))


async def main() -> int:
    s = get_settings()
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with ShadyBankClient(s.bank_api_url) as bank, get_sessionmaker()() as db:
        external = await ledger.get_system_account(db, "EXTERNAL")
        house = await ledger.get_system_account(db, "HOUSE")
        await db.commit()

        cust0 = await bal(bank, CUST_PAN, "1111")
        house0 = await bal(bank, s.house_pan, s.house_pin)
        print(f"start: customer={cust0} house={house0}")

        # 1. Pay: customer's token credits the house (one-shot sale). No OTP needed for credit.
        ctoken = await bank.login(pan=CUST_PAN, otp=pyotp.TOTP(CUST_TOTP).now())
        await bank.credit(ctoken, PRICE, pan=s.house_pan, description="cd:order:test")
        check("customer charged", await bal(bank, CUST_PAN, "1111"), cust0 - PRICE)
        check("house received sale", await bal(bank, s.house_pan, s.house_pin), house0 + PRICE)

        # 2. Ledger records EXTERNAL -> HOUSE
        await ledger.post_tx(db, TxType.SALE, [(external.id, house.id, int(PRICE * 100))])
        await db.commit()
        check("house ledger == sale", await ledger.balance_cents(db, house.id), int(PRICE * 100))

        # 3. Send the food photo email (dev mode logs it if no Resend key)
        try:
            await mailer.send_order_email(
                to="hungry@toorcamp.example", subject="Your CampDash has arrived 🍔",
                html=mailer.order_email_html("Shady Smash Burger", 1, "12.00", "Tent 7, Field B"),
                photo_path=None,  # no photo yet in Phase 0
            )
            sent = True
        except Exception as e:  # noqa: BLE001
            print("  email error:", e)
            sent = False
        check("order email sent (or dev-logged)", sent, True)

    print()
    print(f"RESULT: {FAIL if _fail else PASS}" + (f" — {_fail} failed" if _fail else " — Phase 0 verified (charge + email)"))
    return 1 if _fail else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
