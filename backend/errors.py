from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, status
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


class KonnectException(Exception):
    """Konnect main exception"""


def create_exception_handler(
    status_code: int, detail: Any
) -> Callable[[Request, Exception], JSONResponse]:
    async def exception_handler(request: Request, exc: KonnectException):
        return JSONResponse(content=detail, status_code=status_code)

    return exception_handler


def require_error(app: FastAPI):
    @app.exception_handler(500)
    async def server_exception(request, exc):
        return JSONResponse(
            content={
                "message": "Oops! something went wrong",
                "error_code": "server_error",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_exception(request, exc):
        return JSONResponse(
            content={
                "message": "Oops! Something went wrong",
                "error_code": "server_error",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
