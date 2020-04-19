import logging

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
