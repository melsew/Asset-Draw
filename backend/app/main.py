"""Asset-Draw API entry point.

Registers all routers under /api/v1.  Business logic lives in domain modules;
this file only wires dependencies together.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.admin.router import router as admin_router
from app.assets.router import router as assets_router
from app.auth.router import admin_router as auth_admin_router
from app.auth.router import router as auth_router
from app.campaigns.router import router as campaigns_router
from app.core import health
from app.core.config import get_settings
from app.core.request_id import RequestIdMiddleware
from app.draws.router import public_router
from app.draws.router import router as draws_router
from app.entries.router import router as entries_router
from app.payments.router import router as payments_router
from app.users.router import router as users_router
from app.vendors.router import router as vendors_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=f"{settings.app_name} API",
        version="1.0.0",
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        description=(
            "Asset-Draw: A Verifiable Digital Prize-Draw & Promotional Campaign Platform. "
            "See docs/draw-protocol/ for the normative draw specification."
        ),
    )

    # ── Middleware ───────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "X-Chapa-Signature",
            "X-CSRF-Protection",
        ],
        allow_credentials=False,
    )
    app.add_middleware(RequestIdMiddleware)

    if settings.frontend_dist_dir is not None:
        frontend_dir = Path(settings.frontend_dist_dir)
        index_file = frontend_dir / "index.html"
        assets_dir = frontend_dir / "assets"
        if not index_file.is_file() or not assets_dir.is_dir():
            raise RuntimeError(f"Frontend build is incomplete: {frontend_dir}")
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    # ── Routers ──────────────────────────────────────────
    PREFIX = "/api/v1"

    app.include_router(health.router,    prefix=PREFIX)
    app.include_router(auth_router,      prefix=PREFIX)
    app.include_router(auth_admin_router, prefix=PREFIX)
    app.include_router(users_router,     prefix=PREFIX)
    app.include_router(campaigns_router, prefix=PREFIX)
    app.include_router(entries_router,   prefix=PREFIX)
    app.include_router(payments_router,  prefix=PREFIX)
    app.include_router(draws_router,     prefix=PREFIX)
    app.include_router(public_router,    prefix=PREFIX)
    app.include_router(vendors_router,   prefix=PREFIX)
    app.include_router(assets_router,    prefix=PREFIX)
    app.include_router(admin_router,     prefix=PREFIX)

    if settings.frontend_dist_dir is not None:
        @app.get("/{path:path}", include_in_schema=False)
        def frontend_fallback(path: str) -> FileResponse:
            if path == "api" or path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not found")
            return FileResponse(Path(settings.frontend_dist_dir) / "index.html")

    return app


app = create_app()
