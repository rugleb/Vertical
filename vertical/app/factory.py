from enum import Enum
from typing import TypedDict

from starlette.applications import Starlette

from .auth import AuthService, AuthServiceConfig
from .endpoints import add_routes
from .exception_handlers import add_exception_handlers
from .hunter import HunterService, HunterServiceConfig
from .log import setup_logging
from .middlewares import add_middlewares

__all__ = ("create_app", "AppConfig")


class Signal(str, Enum):
    STARTUP = "startup"
    SHUTDOWN = "shutdown"


class AppConfig(TypedDict):
    auth_service: AuthServiceConfig
    hunter_service: HunterServiceConfig


def setup_auth_service(app: Starlette, config: AuthServiceConfig) -> None:
    auth_service = AuthService.from_config(config)
    app.state.auth_service = auth_service

    app.add_event_handler(Signal.STARTUP, auth_service.setup)
    app.add_event_handler(Signal.SHUTDOWN, auth_service.cleanup)


def setup_hunter_service(app: Starlette, config: HunterServiceConfig) -> None:
    hunter_service = HunterService.from_config(config)
    app.state.hunter_service = hunter_service

    app.add_event_handler(Signal.STARTUP, hunter_service.setup)
    app.add_event_handler(Signal.SHUTDOWN, hunter_service.cleanup)


def create_app(config: AppConfig) -> Starlette:
    setup_logging()

    app = Starlette(debug=False)

    add_routes(app)
    add_middlewares(app)
    add_exception_handlers(app)

    setup_auth_service(app, config["auth_service"])
    setup_hunter_service(app, config["hunter_service"])

    return app
