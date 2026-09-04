from enum import IntEnum


class ExitCode(IntEnum):
    OK = 0
    USAGE = 2
    CONFIGURATION = 3
    NOT_READY = 4
    TEMPORARY_FAILURE = 5
    INTERNAL_ERROR = 70


def exit_code_for(error: BaseException) -> ExitCode:
    if isinstance(error, (FileNotFoundError, PermissionError, ValueError)):
        return ExitCode.CONFIGURATION
    if getattr(error, "code", "") in {"workspace_not_ready", "stale_snapshot"}:
        return ExitCode.NOT_READY
    if isinstance(error, (TimeoutError, ConnectionError)):
        return ExitCode.TEMPORARY_FAILURE
    return ExitCode.INTERNAL_ERROR


def error_report(error: BaseException) -> dict[str, object]:
    code = exit_code_for(error)
    return {"status": "error", "exit_code": int(code), "error": code.name.lower()}
