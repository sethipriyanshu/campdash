from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import ledger, models  # noqa: F401  (registers tables on Base.metadata)
from app.config import get_settings
from app.db import Base, get_engine, get_sessionmaker
from app.routers import admin, menu, orders
from app.seed import seed_menu_if_empty
from bank import ShadyBankClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.auto_create_tables:
        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    async with get_sessionmaker()() as db:
        await ledger.get_system_account(db, "EXTERNAL")
        await ledger.get_system_account(db, "HOUSE")
        await db.commit()
        await seed_menu_if_empty(db)
    app.state.bank = ShadyBankClient(settings.bank_api_url)
    try:
        yield
    finally:
        await app.state.bank.aclose()
        await get_engine().dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="CampDash API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
        allow_methods=["*"], allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    async def health() -> dict:
        return {"status": "ok"}

    Path("media").mkdir(exist_ok=True)
    app.mount("/media", StaticFiles(directory="media"), name="media")

    @app.get("/admin", include_in_schema=False)
    async def admin_page() -> FileResponse:
        return FileResponse(Path(__file__).resolve().parent.parent / "admin" / "admin.html")

    app.include_router(menu.router)
    app.include_router(menu.config_router)
    app.include_router(orders.router)
    app.include_router(admin.router)

    # Single-deploy: serve the built mobile UI from the same origin when present.
    web = Path(settings.web_dir)
    if web.is_dir() and (web / "index.html").exists():
        index = web / "index.html"

        @app.get("/", include_in_schema=False)
        async def ui_index() -> FileResponse:
            return FileResponse(index)

        app.mount("/", StaticFiles(directory=str(web), html=True), name="web")

    return app


app = create_app()
