from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from harness_context.api.v2.enums import ErrorCode


@dataclass(frozen=True)
class ErrorDetail:
    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ErrorResponse:
    error: ErrorDetail
    api_version: str = "2.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def map_exception(error: Exception) -> ErrorResponse:
    code = getattr(error, "code", None)
    if isinstance(code, str):
        return ErrorResponse(ErrorDetail(code=code, message=str(error)))
    if isinstance(error, (TypeError, ValueError)):
        return ErrorResponse(ErrorDetail(code=ErrorCode.INVALID_REQUEST.value, message=str(error)))
    return ErrorResponse(ErrorDetail(code=ErrorCode.INTERNAL_ERROR.value, message=str(error)))
