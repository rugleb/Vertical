from functools import wraps
from typing import Dict

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response

from vertical import hdrs

from .adapters import RequestAdapter
from .auth import AuthService
from .hunter import HunterService
from .models import Phone
from .responses import ok
from .types import Endpoint

__all__ = ("add_routes", )


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def get_hunter_service(request: Request) -> HunterService:
    return request.app.state.hunter_service


def get_json(request: Request) -> Dict:
    return request.state.json


def auth(endpoint: Endpoint) -> Endpoint:

    @wraps(endpoint)
    async def wrapper(request: Request) -> Response:
        auth_service = get_auth_service(request)

        request_adapter = RequestAdapter(request)
        await auth_service.authorize(request_adapter)

        return await endpoint(request)

    return wrapper


async def ping(_: Request) -> Response:
    return ok(message="pong")


@auth
async def health(request: Request) -> Response:
    await get_auth_service(request).ping()
    return ok()


@auth
async def phone_reliability(request: Request) -> Response:
    json = get_json(request)
    phone = Phone.from_dict(json)

    hunter = get_hunter_service(request)
    reliability = await hunter.verify(phone.number)

    data = reliability.to_dict()
    return ok(data)


def add_routes(app: Starlette) -> None:
    app.add_route(
        path="/ping",
        route=ping,
        methods=hdrs.METHOD_ALL,
        name="ping",
    )

    app.add_route(
        path="/health",
        route=health,
        methods=hdrs.METHOD_ALL,
        name="health",
    )

    app.add_route(
        path="/reliability/phone",
        route=phone_reliability,
        methods=[
            hdrs.METHOD_POST,
        ],
    )
