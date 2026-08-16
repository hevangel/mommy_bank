"""FastAPI app: API + SPA hosting + health + first-run seed."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import get_config
from .db import Base, SessionLocal, get_engine
from .routers import accounts as accounts_router
from .routers import auth as auth_router
from .routers import loans as loans_router
from .routers import users as users_router
from .routers import exchange_router, settings_router
from .seed import seed
from .services.settings import BankError


@asynccontextmanager
async def lifespan(_: FastAPI):
    engine = get_engine()
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    cfg = get_config()
    app = FastAPI(title="Mommy Bank", version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(BankError)
    async def _bank_error(_: Request, exc: BankError):  # pragma: no cover - glue
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.get("/api/health", tags=["meta"])
    def health():
        return {"status": "ok", "app": "mommybank", "version": "1.0.0"}

    for router in (
        auth_router.router,
        users_router.router,
        accounts_router.router,
        loans_router.router,
        settings_router.router,
        exchange_router.router,
    ):
        app.include_router(router, prefix="/api/v1")

    # ---- SPA hosting (production / docker): serve frontend/dist when present
    dist = Path(cfg.static_dir)
    if (dist / "index.html").exists():
        assets = dist / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa(full_path: str):
            if full_path.startswith("api"):
                return JSONResponse({"detail": "Not found"}, status_code=404)
            candidate = (dist / full_path).resolve()
            try:
                candidate.relative_to(dist.resolve())
            except ValueError:
                return FileResponse(dist / "index.html")
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")

    return app


app = create_app()
