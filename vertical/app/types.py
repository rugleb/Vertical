from typing import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import Response

__all__ = ("Endpoint", )

Endpoint = Callable[[Request], Awaitable[Response]]
