from harness_context.api.v2.errors import ErrorResponse, map_exception


def error_payload(error: Exception) -> dict:
    return map_exception(error).to_dict()


__all__ = ["ErrorResponse", "error_payload", "map_exception"]
