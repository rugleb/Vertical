import logging.config
import sys
from typing import Dict, TypedDict

from marshmallow import EXCLUDE, Schema, fields, post_load

from .context import REQUEST_ID
from .protocols import ResponseProtocol

MISSING = "-"

app_logger = logging.getLogger("app")
audit_logger = logging.getLogger("audit")
access_logger = logging.getLogger("access")
hunter_logger = logging.getLogger("hunter")


class LoggerConfig(TypedDict):
    name: str


class LoggerSchema(Schema):
    name = fields.Str(required=True)

    class Meta:
        unknown = EXCLUDE

    @post_load
    def make_logger(self, data: Dict, **kwargs) -> logging.Logger:
        return logging.getLogger(**data)


class AccessLogger:

    __slots__ = ("_logger",)

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def log(self, response: ResponseProtocol, request_time: float) -> None:
        extra = {
            "request_time": round(request_time, 4),
            "request_id": response.request.identifier,
            "remote_addr": response.request.remote_addr or MISSING,
            "referer": response.request.referer or MISSING,
            "user_agent": response.request.user_agent or MISSING,
            "method": response.request.method,
            "path": response.request.path,
            "response_length": len(response.body),
            "response_code": response.code,
        }
        self._logger.info("Access info", extra=extra)


CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        "root": {
            "level": "INFO",
            "handlers": [
                "console",
            ],
            "propagate": False,
        },
        app_logger.name: {
            "level": "INFO",
            "handlers": [
                "console",
            ],
            "propagate": False,
        },
        access_logger.name: {
            "level": "INFO",
            "handlers": [
                "access",
            ],
            "propagate": False,
        },
        audit_logger.name: {
            "level": "INFO",
            "handlers": [
                "console",
            ],
            "propagate": False,
        },
        hunter_logger.name: {
            "level": "INFO",
            "handlers": [
                "console",
            ],
            "propagate": False,
        },
        "gunicorn.error": {
            "level": "INFO",
            "handlers": [
                "console",
            ],
            "propagate": False,
        },
        "gunicorn.access": {
            "level": "ERROR",
            "handlers": [
                "gunicorn.access",
            ],
            "propagate": False,
        },
        "uvicorn.error": {
            "level": "INFO",
            "handlers": [
                "console",
            ],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": "ERROR",
            "handlers": [
                "gunicorn.access",
            ],
            "propagate": False,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
            "stream": sys.stdout,
            "filters": [
                "request_id",
            ],
        },
        "access": {
            "class": "logging.StreamHandler",
            "formatter": "access",
            "stream": sys.stdout,
            "filters": [
                "request_id",
            ],
        },
        "gunicorn.access": {
            "class": "logging.StreamHandler",
            "formatter": "gunicorn.access",
            "stream": sys.stdout,
            "filters": [
                "request_id",
            ],
        },
    },
    "formatters": {
        "console": {
            "format": (
                'time="%(asctime)s" '
                'level="%(levelname)s" '
                'logger="%(name)s" '
                'pid="%(process)d" '
                'request_id="%(request_id)s" '
                'message="%(message)s"'
            ),
            "datefmt": "%Y.%m.%d %H:%M:%S",
        },
        "access": {
            "format": (
                'time="%(asctime)s" '
                'level="%(levelname)s" '
                'logger="%(name)s" '
                'pid="%(process)d" '
                'request_id="%(request_id)s" '
                'remote_addr="%(remote_addr)s" '
                'referer="%(referer)s" '
                'user_agent="%(user_agent)s" '
                'method="%(method)s" '
                'path="%(path)s" '
                'response_length="%(response_length)d" '
                'response_code="%(response_code)d" '
                'request_time="%(request_time)s" '
            ),
            "datefmt": "%Y.%m.%d %H:%M:%S",
        },
        "gunicorn.access": {
            "format": (
                'time="%(asctime)s" '
                'level="%(levelname)s" '
                'logger="%(name)s" '
                'pid="%(process)d" '
                'request_id="%(request_id)s" '
                '"%(message)s"'
            ),
            "datefmt": "%Y.%m.%d %H:%M:%S",
        },
    },
    "filters": {
        "request_id": {
            "()": "vertical.app.log.RequestIDFilter",
        },
    },
}


class RequestIDFilter(logging.Filter):

    def __init__(self, name: str = ""):
        self.context_var = REQUEST_ID

        super().__init__(name)

    def filter(self, record: logging.LogRecord) -> int:
        setattr(record, "request_id", self.context_var.get())
        return super().filter(record)


def setup_logging() -> None:
    logging.config.dictConfig(CONFIG)
