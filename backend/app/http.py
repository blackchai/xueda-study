from typing import Any

from fastapi import Request


class ApiProblem(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def success(request: Request, data: Any, message: str = "ok") -> dict[str, Any]:
    return {
        "code": 0,
        "message": message,
        "data": data,
        "requestId": request_id(request),
    }

