from datetime import date, datetime
from typing import Any

import structlog
from bson import ObjectId
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

logger = structlog.get_logger()


def _make_json_serializable(obj: Any) -> Any:
    """Recursively convert objects to JSON-serializable form."""
    if obj is None or isinstance(obj, (int, float, bool, str)):
        return obj
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): _make_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_make_json_serializable(v) for v in obj]
    if hasattr(obj, "__dict__"):
        return _make_json_serializable(obj.__dict__)
    return str(obj)


class AppException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            f"{resource} not found: {identifier}",
            status.HTTP_404_NOT_FOUND,
            {"resource": resource, "identifier": identifier},
        )


class ValidationError(AppException):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY, details)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class ConflictError(AppException):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, status.HTTP_409_CONFLICT, details)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    logger.warning(
        "Application exception",
        path=request.url.path,
        message=exc.message,
        details=exc.details,
        status_code=exc.status_code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "details": exc.details},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    safe_errors = _make_json_serializable(exc.errors())
    logger.warning("Validation error", path=request.url.path, errors=safe_errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation error", "details": safe_errors},
    )


async def pydantic_validation_exception_handler(request: Request, exc: PydanticValidationError) -> JSONResponse:
    safe_errors = _make_json_serializable(exc.errors())
    logger.warning("Pydantic validation error", path=request.url.path, errors=safe_errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation error", "details": safe_errors},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(PydanticValidationError, pydantic_validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
