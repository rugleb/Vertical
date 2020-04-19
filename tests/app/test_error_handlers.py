from http import HTTPStatus
from typing import Callable, NoReturn

from sqlalchemy.orm import Session
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.testclient import TestClient

from vertical import hdrs
from vertical.app import auth

APPLICATION_JSON = "application/json"


async def error_endpoint(_: Request) -> NoReturn:
    raise NotImplementedError()


def test_default_error_handler(
        client: TestClient,
        create_request_id: Callable,
        sqlalchemy_auth_session: Session,
) -> None:
    app: Starlette = client.app  # type: ignore

    path = "/error"
    app.add_route(path, error_endpoint)

    request_id = create_request_id()

    headers = {
        hdrs.CONTENT_TYPE: APPLICATION_JSON,
        hdrs.X_REQUEST_ID: request_id,
    }

    r = client.get(path, headers=headers)

    http_status = HTTPStatus.INTERNAL_SERVER_ERROR
    assert r.status_code == http_status

    assert r.json() == {
        "message": "Internal server error",
    }

    assert r.headers[hdrs.X_REQUEST_ID] == request_id

    assert sqlalchemy_auth_session.query(auth.Response).first() is None

    request = sqlalchemy_auth_session.query(auth.Request).first()
    assert isinstance(request, auth.Request)

    assert request.id == request_id
    assert request.path == r.request.path_url
    assert request.method == r.request.method
    assert request.body is None
    assert request.remote == "testclient:50000"


def test_http_exception_handler(
        client: TestClient,
        create_request_id: Callable,
        sqlalchemy_auth_session: Session,
) -> None:
    request_id = create_request_id()

    headers = {
        hdrs.CONTENT_TYPE: APPLICATION_JSON,
        hdrs.X_REQUEST_ID: request_id,
    }

    r = client.get("undefined", headers=headers)

    http_status = HTTPStatus.NOT_FOUND
    assert r.status_code == http_status

    assert r.json() == {
        "message": "Not Found",
    }

    assert r.headers[hdrs.X_REQUEST_ID] == request_id

    response = sqlalchemy_auth_session.query(auth.Response).first()
    assert isinstance(response, auth.Response)

    assert response.id == request_id
    assert response.body == r.json()
    assert response.code == r.status_code

    assert response.request.id == request_id
    assert response.request.path == r.request.path_url
    assert response.request.method == r.request.method
    assert response.request.body is None
    assert response.request.remote == "testclient:50000"
