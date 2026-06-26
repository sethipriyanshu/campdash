#!/usr/bin/env python3
"""CampDash Phase 3: admin page + admin API + per-card rate limit.

Prereqs: local shadybank up (:8021), CampDash API up (:8013) on the Alembic schema.
    ./.venv/bin/python scripts/test_phase3.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

API = "http://127.0.0.1:8013"
ADMIN = {"X-Admin-Key": "codedaycodeday12"}

PASS, FAIL = "\033[32mPASS\033[0m", "\033[31mFAIL\033[0m"
_fail = 0


def check(label, got, want):
    global _fail
    ok = got == want
    _fail += 0 if ok else 1
    print(f"  [{PASS if ok else FAIL}] {label}: got {got!r}, want {want!r}")


async def main() -> int:
    async with httpx.AsyncClient(base_url=API, timeout=20) as api:
        check("/admin page serves", (await api.get("/admin")).status_code, 200)
        check("admin API needs key (403)", (await api.get("/api/admin/orders")).status_code, 403)
        check("admin API with key (200)", (await api.get("/api/admin/orders", headers=ADMIN)).status_code, 200)

        # Per-card rate limit: hammer with a bad card; should flip to 429 within the cap (8/300s).
        print("Rate limit (per card)")
        codes = []
        for i in range(12):
            r = await api.post("/api/orders", json={
                "item_id": "00000000-0000-0000-0000-000000000000", "qty": 1,
                "email": "x@y.com", "address": "z", "pan": "0000000000000000",
                "otp": "000000", "idempotency_key": f"rl-order-{i:04d}",
            })
            codes.append(r.status_code)
        check("eventually rate-limited (429)", 429 in codes, True)

    print()
    print(f"RESULT: {FAIL if _fail else PASS}" + (f" — {_fail} failed" if _fail else " — Phase 3 verified"))
    return 1 if _fail else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
