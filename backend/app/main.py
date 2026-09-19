from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analyze, challenge, pow
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(analyze.router)
    app.include_router(pow.router)
    app.include_router(challenge.router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": settings.app_name, "version": "0.1.0"}

    return app


app = create_app()
