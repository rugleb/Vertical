from typing import Optional, Protocol

__all__ = ("RequestProtocol", "ResponseProtocol")


class RequestProtocol(Protocol):
    identifier: Optional[str]
    method: str
    path: str
    body: Optional[str]
    remote_addr: Optional[str]
    referer: Optional[str]
    user_agent: Optional[str]
    authorization: Optional[str]


class ResponseProtocol(Protocol):
    request: RequestProtocol
    body: str
    code: int
