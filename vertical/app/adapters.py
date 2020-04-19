from starlette.requests import Request
from starlette.responses import Response

from vertical import hdrs

from .protocols import RequestProtocol, ResponseProtocol

__all__ = ("RequestAdapter", "ResponseAdapter")


class RequestAdapter(RequestProtocol):

    __slots__ = (
        "identifier",
        "method",
        "path",
        "body",
        "remote_addr",
        "referer",
        "user_agent",
        "authorization",
    )

    def __init__(self, request: Request):
        self.identifier = request.headers.get(hdrs.X_REQUEST_ID)

        self.method = request.method
        self.path = request.url.path

        body = request.state.body
        self.body = body.decode("utf-8") if body else None

        self.referer = request.headers.get(hdrs.REFERER)

        host, port = request.client
        self.remote_addr = f"{host}:{port}"

        user_agent = request.headers.get(hdrs.USER_AGENT, "")
        self.user_agent = user_agent[:64]

        self.authorization = request.headers.get(hdrs.AUTHORIZATION)


class ResponseAdapter(ResponseProtocol):

    __slots__ = (
        "request",
        "body",
        "code",
    )

    def __init__(self, request: RequestAdapter, response: Response):
        self.request = request

        self.body = response.body.decode("utf-8")
        self.code = response.status_code
