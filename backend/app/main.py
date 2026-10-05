import logging

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import ai, analytics, auth, customers, imports, invoices, products
from app.core.config import get_settings
from app.core.db import engine
from app.core.errors import register_error_handlers

logging.basicConfig(level=logging.INFO)
settings = get_settings()
settings.validate_for_runtime()

app = FastAPI(title="VyapaarOS API", version="1.0.0",
              docs_url=None if settings.environment == "production" else "/docs",
              redoc_url=None, openapi_url=None if settings.environment == "production" else "/openapi.json")
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type"])
register_error_handlers(app)

api = APIRouter(prefix="/api")
for module in (auth, analytics, customers, products, invoices, imports, ai):
    api.include_router(module.router)
app.include_router(api)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
def health_db() -> dict[str, str]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"status": "unavailable"})  # type: ignore[return-value]
    return {"status": "ok"}
