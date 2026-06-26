from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from app.config import get_settings
from bank import ShadyBankClient


def get_bank(request: Request) -> ShadyBankClient:
    return request.app.state.bank


def require_admin(request: Request) -> None:
    if request.headers.get("X-Admin-Key", "") != get_settings().admin_key:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin key required")
