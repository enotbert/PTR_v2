"""API error type and FastAPI exception handler (flat JSON body)."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """Raised for expected client errors.

    Serialized as ``error`` and ``message``, with optional structured ``details``.
    """

    def __init__(
        self,
        status_code: int,
        error: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.error = error
        self.message = message
        self.details = details
        super().__init__(message)


def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    body: dict[str, Any] = {"error": exc.error, "message": exc.message}
    if exc.details is not None:
        body["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=body)


def http_error_dict(status_code: int, error: str, message: str) -> dict[str, Any]:
    """OpenAPI `responses` example payload."""
    return {"error": error, "message": message, "status_code": status_code}
