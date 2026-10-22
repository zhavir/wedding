from contextlib import asynccontextmanager
from typing import Annotated
from urllib.parse import urlsplit

from botocore.exceptions import ClientError
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.views import setup_admin
from app.core.config import settings
from app.db.session import get_db
from app.routers import admin, auth, calendar, photos, rsvps


@asynccontextmanager
async def lifespan(app):
    setup_admin(app)
    yield


app = FastAPI(
    lifespan=lifespan, title="Our wedding", docs_url=None, redoc_url=None, openapi_url=None
)
for router in [auth.router, rsvps.router, photos.router, admin.router, calendar.router]:
    app.include_router(router, prefix="/api")


@app.middleware("http")
async def security(request: Request, call_next):
    # CloudFront forwards viewer cookies and Origin, but API Gateway needs its own Host.
    # Restore only our configured canonical host, never a caller-supplied forwarded host.
    if settings().dsql_host:
        canonical = urlsplit(settings().site_url)
        request.scope["scheme"] = canonical.scheme
        request.scope["server"] = (canonical.hostname, canonical.port or 443)
        request.scope["headers"] = [
            (key, value) for key, value in request.scope["headers"] if key != b"host"
        ] + [(b"host", canonical.netloc.encode("ascii"))]

    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if request.url.path.startswith("/api/admin") and not origin:
            return JSONResponse(
                status_code=403,
                content={"detail": "An origin header is required for admin changes."},
            )
        if (
            origin and origin not in [settings().site_url, *settings().allowed_origins.split(",")]
        ) or request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse(
                status_code=403, content={"detail": "Request origin is not allowed."}
            )
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = (
        "same-origin" if request.url.path.startswith("/api/admin") else "no-referrer"
    )
    return response


@app.exception_handler(ClientError)
async def aws_error(request: Request, exc: ClientError):
    return JSONResponse(
        status_code=503, content={"detail": "Temporarily unavailable. Please try again shortly."}
    )


@app.exception_handler(DBAPIError)
async def database_error(request: Request, exc: DBAPIError):
    return JSONResponse(
        status_code=503,
        headers={"Retry-After": "1"},
        content={"detail": "Please retry; the database is temporarily busy."},
    )


@app.get("/api/health")
async def health(db: Annotated[AsyncSession, Depends(get_db)]):
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}
