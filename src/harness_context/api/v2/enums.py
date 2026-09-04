from __future__ import annotations

from enum import Enum


class ContextStrategy(str, Enum):
    AUTO = "auto"


class Freshness(str, Enum):
    CURRENT = "current"


class ErrorCode(str, Enum):
    INTERNAL_ERROR = "internal_error"
    INVALID_REQUEST = "invalid_request"
    NOT_FOUND = "not_found"
