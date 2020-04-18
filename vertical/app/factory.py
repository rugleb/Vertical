from enum import Enum
from typing import TypedDict

from starlette.applications import Starlette

from .auth import AuthService, AuthServiceConfig

__all__ = ("create_app", "AppConfig")


class Signal(str, Enum):
    STARTUP = "startup"
    SHUTDOWN = "shutdown"


class AppConfig(TypedDict):
    auth: AuthServiceConfig


def setup_auth_service(app: Starlette, config: AuthServiceConfig) -> None:
    auth_service = AuthService.from_config(config)
    app.state.auth_service = auth_service

    app.add_event_handler(Signal.STARTUP, auth_service.setup)
    app.add_event_handler(Signal.SHUTDOWN, auth_service.cleanup)


def create_app(config: AppConfig) -> Starlette:
    app = Starlette(debug=False)

    setup_auth_service(app, config["auth"])

    return app
