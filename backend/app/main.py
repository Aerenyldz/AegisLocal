from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, make_asgi_app

from app.api import analyze, challenge, pow
from app.core.config import get_settings

REQUESTS = Counter(
    "aegis_http_requests_total",
    "Total HTTP requests handled by AegisLocal.",
    ("method", "path", "status"),
)
LATENCY = Histogram(
    "aegis_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ("method", "path"),
)


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

    @app.middleware("http")
    async def observe_requests(request, call_next):
        started = perf_counter()
        response = await call_next(request)
        path = request.url.path
        REQUESTS.labels(request.method, path, str(response.status_code)).inc()
        LATENCY.labels(request.method, path).observe(perf_counter() - started)
        return response

    app.include_router(analyze.router)
    app.include_router(pow.router)
    app.include_router(challenge.router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": settings.app_name, "version": "0.1.0"}

    @app.get("/")
    async def root():
        return {
            "service": settings.app_name,
            "status": "ok",
            "docs": "/docs",
            "health": "/health",
        }

    app.mount("/metrics", make_asgi_app())
    return app


app = create_app()
