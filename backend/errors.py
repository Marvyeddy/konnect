from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, status
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


class KonnectException(Exception):
    """Konnect main exception"""


class UserAlreadyExists(KonnectException):
    """User already exists"""


class UserCredentialInvalid(KonnectException):
    """Credentials are wrong"""


class ConfirmPasswordException(KonnectException):
    """New password and confirm password do not match"""


class TokenException(KonnectException):
    """Token is missing"""


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

    app.add_exception_handler(
        UserAlreadyExists,
        create_exception_handler(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "User with credential already exists",
                "error": "user_already_exists",
            },
        ),
    )

    app.add_exception_handler(
        UserCredentialInvalid,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "User credential invalid",
                "error": "credential_invalid",
            },
        ),
    )

    app.add_exception_handler(
        ConfirmPasswordException,
        create_exception_handler(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "New password and confirm password do not match.",
                "error": "confirm_password_error",
            },
        ),
    )

    app.add_exception_handler(
        TokenException,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Token is missing", "error": "token_missing"},
        ),
    )
