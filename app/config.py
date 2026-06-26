from __future__ import annotations

import os
import warnings

from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_DB = "postgresql+asyncpg://campdash:campdash@localhost:5436/campdash"


def _normalize_db_url(url: str) -> str:
    """Managed hosts hand out postgres://… or postgresql://… (often with ?sslmode=require, which
    asyncpg rejects). Coerce to the asyncpg driver and strip libpq-only query params; SSL itself
    is configured in db.py for remote hosts."""
    import re

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    # Drop sslmode / channel_binding query params asyncpg doesn't understand.
    url = re.sub(r"[?&](sslmode|channel_binding|target_session_attrs)=[^&]*", "", url)
    url = url.replace("?&", "?").rstrip("?&")
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CD_", extra="ignore")

    database_url: str = _DEFAULT_DB

    # shadybank money rail
    bank_api_url: str = "http://127.0.0.1:8021"
    house_pan: str = "8997000000000002"   # sales land here (live: 8997986672600085)
    house_pin: str = "4242"               # local dev only; live house uses a runtime OTP

    # Email. Provider auto-selected: SMTP if smtp_host+user set, else Resend if api key set,
    # else dev mode (logs instead of sending).
    resend_api_key: str = ""
    mail_from: str = "CampDash <onboarding@resend.dev>"
    # Gmail SMTP: host smtp.gmail.com, port 587, user = your gmail, password = a Google App Password.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    # Security
    fernet_key: str = ""
    admin_key: str = "dev-admin-key"

    # Delivery fee added on top at checkout (30%). Charged to the house along with the item price.
    delivery_fee_bps: int = 3000

    # Abuse limits on checkout (per card number).
    order_max_attempts: int = 8
    order_window_seconds: int = 300

    auto_create_tables: bool = True
    web_dir: str = "web"
    env: str = "dev"
    cors_origins: list[str] = ["*"]


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        s = Settings()
        # If CD_DATABASE_URL wasn't set, fall back to any DB URL the host injected (managed Postgres).
        if s.database_url == _DEFAULT_DB:
            for key in ("DATABASE_URL", "DATABASE_PUBLIC_URL", "POSTGRES_URL"):
                if os.environ.get(key):
                    s.database_url = os.environ[key]
                    break
        s.database_url = _normalize_db_url(s.database_url)  # coerce driver + strip libpq-only params
        if not s.fernet_key:
            if s.env != "dev":
                raise RuntimeError("CD_FERNET_KEY is required outside dev")
            from cryptography.fernet import Fernet

            s.fernet_key = Fernet.generate_key().decode()
            warnings.warn("No CD_FERNET_KEY set; generated an ephemeral dev key.")
        _settings = s
    return _settings
