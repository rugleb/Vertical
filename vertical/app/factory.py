from enum import Enum
from typing import TypedDict

from starlette.applications import Starlette

from .alchemy import SQLAlchemyStorage, SQLAlchemyStorageConfig
from .auth import AuthService, AuthServiceConfig
from .hunter import PhoneService, PhoneServiceConfig

__all__ = ("create_app", "AppConfig")


class Signal(str, Enum):
    STARTUP = "startup"
    SHUTDOWN = "shutdown"


class AppConfig(TypedDict):
    auth_service: AuthServiceConfig
    hunter_db: SQLAlchemyStorageConfig
    phone_service: PhoneServiceConfig


def setup_auth_service(app: Starlette, config: AuthServiceConfig) -> None:
    auth_service = AuthService.from_config(config)
    app.state.auth_service = auth_service

    app.add_event_handler(Signal.STARTUP, auth_service.setup)
    app.add_event_handler(Signal.SHUTDOWN, auth_service.cleanup)


def setup_hunter_db(app: Starlette, config: SQLAlchemyStorageConfig) -> None:
    hunter_db = SQLAlchemyStorage.from_config(config)
    app.state.hunter_db = hunter_db

    app.add_event_handler(Signal.STARTUP, hunter_db.setup)
    app.add_event_handler(Signal.SHUTDOWN, hunter_db.cleanup)


def setup_phone_service(app: Starlette, config: PhoneServiceConfig) -> None:
    phone_service = PhoneService.from_config(config)
    app.state.phone_service = phone_service


def create_app(config: AppConfig) -> Starlette:
    app = Starlette(debug=False)

    setup_auth_service(app, config["auth_service"])
    setup_hunter_db(app, config["hunter_db"])
    setup_phone_service(app, config["phone_service"])

    return app
