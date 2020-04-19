from functools import wraps

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response

from vertical import hdrs

from .adapters import RequestAdapter
from .auth import AuthService
from .models import Phone
from .responses import ok
from .types import Endpoint

__all__ = ("add_routes", )


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def auth(endpoint: Endpoint) -> Endpoint:

    @wraps(endpoint)
    async def wrapper(request: Request) -> Response:
        auth_service = get_auth_service(request)

        request_adapter = RequestAdapter(request)
        await auth_service.authorize(request_adapter)

        return await endpoint(request)

    return wrapper


@auth
async def ping(request: Request) -> Response:
    await get_auth_service(request).ping()
    return ok(message="pong")


@auth
async def phone_reliability(request: Request) -> Response:
    json = request.state.json
    phone = Phone.from_dict(json)

    reliability_service = request.app.state.reliability_service
    hunter_session = request.state.hunter_session

    reliability = reliability_service.verify(phone, hunter_session)
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
        path="/reliability/phone",
        route=phone_reliability,
        methods=[
            hdrs.METHOD_POST,
        ],
    )
