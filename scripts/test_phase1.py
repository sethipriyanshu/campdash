#!/usr/bin/env python3
"""CampDash Phase 1: public menu + order checkout (charge + email photo + idempotency).

Prereqs: local shadybank up (:8021, test card funded), CampDash API up (:8013), app DB reset.
    ./.venv/bin/python scripts/test_phase1.py
"""
from __future__ import annotations

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

import httpx
import pyotp

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import get_settings  # noqa: E402
from bank import ShadyBankClient  # noqa: E402

API = "http://127.0.0.1:8013"
CUST_PAN, CUST_TOTP = "8997000000000001", "JBSWY3DPEHPK3PXP"

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
    async with httpx.AsyncClient(base_url=API, timeout=20) as api, ShadyBankClient(s.bank_api_url) as bank:
        # 1. Public menu
        print("1. Public menu")
        menu = (await api.get("/api/menu")).json()
        check("menu has items", len(menu) >= 1, True)
        item = menu[0]
        check("item has price + photo", bool(item["price_cents"] and item["photo_path"]), True)
        print(f"   first item: {item['name']} @ {item['price']} SB, photo {item['photo_path']}")
        # photo is served
        check("photo served", (await api.get(item["photo_path"])).status_code, 200)

        cust0 = await bal(bank, CUST_PAN, "1111")
        house0 = await bal(bank, s.house_pan, s.house_pin)

        # 2. Order it
        print("2. Place order")
        otp = pyotp.TOTP(CUST_TOTP).now()
        r = await api.post("/api/orders", json={
            "item_id": item["id"], "qty": 2, "email": "hungry@toorcamp.example",
            "address": "Tent 7, Dusty Field B", "pan": CUST_PAN, "otp": otp,
            "idempotency_key": "p1-order-0001",
        })
        r.raise_for_status()
        o = r.json()
        total = item["price_cents"] * 2
        check("order total = price*qty", o["total_cents"], total)
        check("status PAID", o["status"], "PAID")
        check("emailed (dev-logged)", o["emailed"], True)

        # 3. Money moved
        check("customer charged", await bal(bank, CUST_PAN, "1111"), cust0 - Decimal(total) / 100)
        check("house received", await bal(bank, s.house_pan, s.house_pin), house0 + Decimal(total) / 100)

        # 4. Idempotent re-submit (same key) -> no double charge
        print("3. Idempotency")
        r = await api.post("/api/orders", json={
            "item_id": item["id"], "qty": 2, "email": "hungry@toorcamp.example",
            "address": "Tent 7, Dusty Field B", "pan": CUST_PAN, "otp": otp,
            "idempotency_key": "p1-order-0001",
        })
        r.raise_for_status()
        check("same order id (idempotent)", r.json()["order_id"], o["order_id"])
        check("no extra charge", await bal(bank, CUST_PAN, "1111"), cust0 - Decimal(total) / 100)

        # 5. Bad email rejected
        r = await api.post("/api/orders", json={
            "item_id": item["id"], "qty": 1, "email": "not-an-email",
            "address": "x", "pan": CUST_PAN, "otp": "000000", "idempotency_key": "p1-bademail-1",
        })
        check("bad email -> 422", r.status_code, 422)

        # 6. Admin sees the order + sales total
        print("4. Admin orders")
        adm = (await api.get("/api/admin/orders", headers={"X-Admin-Key": "codedaycodeday12"})).json()
        check("admin lists order", adm["count"] >= 1, True)
        check("sales total counted", adm["sales_total_cents"] >= total, True)

    print()
    print(f"RESULT: {FAIL if _fail else PASS}" + (f" — {_fail} failed" if _fail else " — Phase 1 verified"))
    return 1 if _fail else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
