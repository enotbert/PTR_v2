"""API error type and FastAPI exception handler (flat JSON body)."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """Raised for expected client errors; serialized as {error, message}."""

    def __init__(self, status_code: int, error: str, message: str) -> None:
        self.status_code = status_code
        self.error = error
        self.message = message
        super().__init__(message)


def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "message": exc.message},
    )


def http_error_dict(status_code: int, error: str, message: str) -> dict[str, Any]:
    """OpenAPI `responses` example payload."""
    return {"error": error, "message": message, "status_code": status_code}
