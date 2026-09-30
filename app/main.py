"""Application entry point.

Run with:  uvicorn app.main:app --reload
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import models as _models  # noqa: F401  (registers models on Base.metadata)
from app.database import Base, engine
from app.exceptions import AppError
from app.routers import students

logger = logging.getLogger("student_management")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)  # fine for this scope; use Alembic in production
    yield


app = FastAPI(
    title="Student Management API",
    version="1.0.0",
    description="CRUD API for managing students.",
    lifespan=lifespan,
)
app.include_router(students.router)


def _error(
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, str]] | None = None,
) -> JSONResponse:
    body: dict[str, dict[str, str | list[dict[str, str]]]] = {
        "error": {"code": code, "message": message}
    }
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    return _error(exc.status_code, exc.code, exc.message)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    details: list[dict[str, str]] = [
        {
            "field": ".".join(str(p) for p in e["loc"][1:]) or "body",
            "message": str(e["msg"]).removeprefix("Value error, "),
        }
        for e in exc.errors()
    ]
    return _error(422, "validation_error", "Request validation failed.", details)


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = "not_found" if exc.status_code == 404 else "http_error"
    return _error(exc.status_code, code, str(exc.detail))


@app.exception_handler(Exception)
async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error", exc_info=exc)
    return _error(500, "internal_error", "An unexpected error occurred.")


@app.get("/health", tags=["Health"], summary="Liveness check")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"message": "Student Management API is running. See /docs"}
