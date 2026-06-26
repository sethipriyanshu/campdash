"""Log in as the house account at the bank. Live: a runtime OTP the admin supplies; dev: PIN."""
from __future__ import annotations

from app.config import get_settings
from bank import ShadyBankClient


async def house_login(bank: ShadyBankClient, otp: str | None = None) -> str:
    s = get_settings()
    if otp:
        return await bank.login(pan=s.house_pan, otp=otp)
    return await bank.login(pan=s.house_pan, pin=s.house_pin)
