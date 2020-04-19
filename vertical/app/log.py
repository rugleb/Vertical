import logging
import sys

from .protocols import ResponseProtocol

MISSING = "-"

app_logger = logging.getLogger("app")
audit_logger = logging.getLogger("audit")
access_logger = logging.getLogger("access")


class AccessLogger:

    __slots__ = ("logger", )

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def log(self, response: ResponseProtocol, request_time: float) -> None:
        extra = {
            "request_time": request_time,
            "request_id": response.request.identifier or MISSING,
            "remote_addr": response.request.remote_addr or MISSING,
            "referer": response.request.referer or MISSING,
            "user_agent": response.request.user_agent or MISSING,
            "method": response.request.method,
            "path": response.request.path,
            "response_length": len(response.body),
            "response_code": response.code,
        }

        self.logger.info("Access info", extra=extra)


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
        "gunicorn.error": {
            "level": "INFO",
            "handlers": [
                "console",
            ],
            "propagate": False,
        },
        "gunicorn.access": {
            "level": "INFO",
            "handlers": [
                "access",
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
                "console",
            ],
            "propagate": False,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
            "stream": sys.stdout,
        },
        "access": {
            "class": "logging.StreamHandler",
            "formatter": "access",
            "stream": sys.stdout,
        },
    },
    "formatters": {
        "console": {
            "format": (
                'time="%(asctime)s" '
                'level="%(levelname)s" '
                'logger="%(name)s" '
                'pid="%(process)d" '
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
    },
}
