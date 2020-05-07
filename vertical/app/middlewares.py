import time
from typing import AsyncIterator, Sequence

import orjson
from starlette.applications import Starlette
from starlette.middleware import base
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

from vertical import hdrs

from .adapters import RequestAdapter, ResponseAdapter
from .auth import AuthService
from .context import REQUEST_ID
from .log import AccessLogger, access_logger, app_logger
from .responses import bad_request, server_error, unsupported_media_type
from .utils import make_request_id

__all__ = ("add_middlewares", )


class RequestIdentifierMiddleware(base.BaseHTTPMiddleware):

    async def dispatch(
        self,
        request: Request,
        handler: base.RequestResponseEndpoint,
    ) -> Response:
        request_id = make_request_id()

        token = REQUEST_ID.set(request_id)
        request.state.identifier = request_id

        response = await handler(request)
        response.headers[hdrs.X_REQUEST_ID] = request_id

        REQUEST_ID.reset(token)

        return response


class ExceptionHandlerMiddleware(base.BaseHTTPMiddleware):

    async def dispatch(
        self,
        request: Request,
        handler: base.RequestResponseEndpoint,
    ) -> Response:
        try:
            return await handler(request)
        except Exception as e:
            name = e.__class__.__name__
            app_logger.error(f"Caught unhandled {name} exception: {e}")
            return server_error()


class ContentTypeMiddleware(base.BaseHTTPMiddleware):

    async def dispatch(
        self,
        request: Request,
        handler: base.RequestResponseEndpoint,
    ) -> Response:
        content_type = request.headers.get(hdrs.CONTENT_TYPE)

        if not content_type:
            message = "Content-Type header not recognized"
            app_logger.warning(message)
            return bad_request(message)

        if not content_type.startswith("application/json"):
            app_logger.warning(f"Unsupported Content-Type: {content_type}")
            return unsupported_media_type()

        return await handler(request)


class JsonParserMiddleware(base.BaseHTTPMiddleware):

    async def dispatch(
        self,
        request: Request,
        handler: base.RequestResponseEndpoint,
    ) -> Response:
        body = await request.body()

        try:
            json = orjson.loads(body)
        except ValueError:
            if body:
                message = "Could not parse request body"
                app_logger.warning(message)
                return bad_request(message)
            json = {}

        request.state.body = body
        request.state.json = json

        return await handler(request)


class AccessMiddleware(base.BaseHTTPMiddleware):

    def __init__(
        self,
        app: base.ASGIApp,
        dispatch: base.DispatchFunction = None,
        *,
        ignore_paths: Sequence[str] = None,
    ):
        super().__init__(app, dispatch)

        self.ignore_paths = set(ignore_paths) if ignore_paths else set()
        self.logger = AccessLogger(access_logger)

    async def dispatch(
        self,
        request: Request,
        handler: base.RequestResponseEndpoint,
    ) -> Response:
        started_at = time.perf_counter()

        if request.url.path in self.ignore_paths:
            return await handler(request)

        auth_service: AuthService = request.app.state.auth_service

        request_adapter = RequestAdapter(request)
        await auth_service.save_request(request_adapter)

        streaming: StreamingResponse = await handler(request)  # type: ignore
        response: Response = await resolve_response(streaming)

        # TODO: we should try to do this in the background
        response_adapter = ResponseAdapter(request_adapter, response)
        await auth_service.save_response(response_adapter)

        request_time = time.perf_counter() - started_at
        self.logger.log(response_adapter, request_time)

        return response


async def read_bytes(generator: AsyncIterator[bytes]) -> bytes:
    body = b""
    async for data in generator:
        body += data
    return body


async def resolve_response(streaming: StreamingResponse) -> Response:
    content = await read_bytes(streaming.body_iterator)
    status_code = streaming.status_code
    headers = dict(streaming.headers) if streaming.headers else None
    media_type = "application/json"
    background = streaming.background
    return Response(content, status_code, headers, media_type, background)


def add_middlewares(app: Starlette) -> None:
    app.add_middleware(AccessMiddleware, ignore_paths=["/ping"])
    app.add_middleware(JsonParserMiddleware)
    app.add_middleware(ContentTypeMiddleware)
    app.add_middleware(ExceptionHandlerMiddleware)
    app.add_middleware(RequestIdentifierMiddleware)
