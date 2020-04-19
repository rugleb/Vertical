from marshmallow import ValidationError
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from .auth import AuthException
from .responses import create_response, validation_error

__all__ = ("add_exception_handlers", )


async def http_exception_handler(_: Request, e: HTTPException) -> Response:
    content = {
        "message": e.detail,
    }
    return create_response(content, e.status_code)


async def auth_exception_handler(_: Request, e: AuthException) -> Response:
    content = {
        "message": e.render(),
    }
    return create_response(content, e.http_status)


async def validation_error_handler(_: Request, e: ValidationError) -> Response:
    errors = e.messages
    return validation_error(errors)


def add_exception_handlers(app: Starlette) -> None:
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(AuthException, auth_exception_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
