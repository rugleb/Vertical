from http import HTTPStatus
from typing import Callable, Dict

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vertical import hdrs
from vertical.app.auth import Request, Response

APPLICATION_JSON = "application/json"


class TestRequestIdentifierMiddleware:
    path = "/ping"

    def test_request_without_request_id(
            self,
            client: TestClient,
            sqlalchemy_auth_session: Session,
    ) -> None:
        r = client.get(self.path)

        http_status = HTTPStatus.BAD_REQUEST
        assert r.status_code == http_status

        assert r.json() == {
            "message": "X-Request-Id header not recognized",
        }

        assert hdrs.X_REQUEST_ID not in r.headers

        assert sqlalchemy_auth_session.query(Request).first() is None
        assert sqlalchemy_auth_session.query(Response).first() is None

    @pytest.mark.parametrize("request_id", [
        "a8098c1af86e11da3d1a00112444be1e",
        "a8098c1af86e11da3d1a0",
        "uuid",
    ])
    def test_request_with_invalid_request_id_format(
            self,
            client: TestClient,
            sqlalchemy_auth_session: Session,
            request_id: str,
    ) -> None:
        headers = {
            hdrs.X_REQUEST_ID: request_id,
        }

        r = client.get(self.path, headers=headers)

        http_status = HTTPStatus.BAD_REQUEST
        assert r.status_code == http_status

        assert r.json() == {
            "message": "X-Request-Id header must be in UUID format",
        }

        assert hdrs.X_REQUEST_ID not in r.headers

        assert sqlalchemy_auth_session.query(Request).first() is None
        assert sqlalchemy_auth_session.query(Response).first() is None

    def test_request_with_valid_request_id_format(
            self,
            client: TestClient,
            sqlalchemy_auth_session: Session,
            create_request_id: Callable,
    ) -> None:
        request_id = create_request_id()

        headers = {
            hdrs.X_REQUEST_ID: request_id,
            hdrs.CONTENT_TYPE: APPLICATION_JSON,
        }

        r = client.get(self.path, headers=headers)

        http_status = HTTPStatus.OK
        assert r.status_code == http_status

        assert r.headers[hdrs.X_REQUEST_ID] == request_id

        assert sqlalchemy_auth_session.query(Response).first() is None
        assert sqlalchemy_auth_session.query(Request).first() is None


class TestContentTypeMiddleware:
    url = "/ping"

    def test_request_without_content_type(
            self,
            client: TestClient,
            create_request_id: Callable,
            sqlalchemy_auth_session: Session,
    ) -> None:
        request_id = create_request_id()

        headers = {
            hdrs.X_REQUEST_ID: request_id,
        }

        response = client.get(self.url, headers=headers)

        http_status = HTTPStatus.BAD_REQUEST
        assert response.status_code == http_status

        assert response.json() == {
            "message": "Content-Type header not recognized",
        }

        assert sqlalchemy_auth_session.query(Response).first() is None
        assert sqlalchemy_auth_session.query(Request).first() is None

    def test_request_without_invalid_content_type(
            self,
            client: TestClient,
            create_request_id: Callable,
            sqlalchemy_auth_session: Session,
    ) -> None:
        request_id = create_request_id()

        headers = {
            hdrs.X_REQUEST_ID: request_id,
            hdrs.CONTENT_TYPE: "application/html",
        }

        response = client.get(self.url, headers=headers)

        http_status = HTTPStatus.UNSUPPORTED_MEDIA_TYPE
        assert response.status_code == http_status

        assert response.json() == {
            "message": "Unsupported media type",
        }

        assert sqlalchemy_auth_session.query(Response).first() is None
        assert sqlalchemy_auth_session.query(Request).first() is None


class TestJsonDecoderMiddleware:
    url = "/ping"

    def test_request_without_body(
            self,
            client: TestClient,
            headers: Dict,
            sqlalchemy_auth_session: Session,
    ) -> None:
        response = client.post(self.url, headers=headers)

        http_status = HTTPStatus.OK
        assert response.status_code == http_status

        assert response.json() == {
            "message": "pong",
            "data": {},
        }

        assert sqlalchemy_auth_session.query(Response).first() is None
        assert sqlalchemy_auth_session.query(Request).first() is None

    def test_request_with_invalid_json_body(
            self,
            client: TestClient,
            headers: Dict,
            sqlalchemy_auth_session: Session,
    ) -> None:
        data = "{key:value}"
        response = client.post(self.url, headers=headers, data=data)

        http_status = HTTPStatus.BAD_REQUEST
        assert response.status_code == http_status

        assert response.json() == {
            "message": "Could not parse request body",
        }

        assert sqlalchemy_auth_session.query(Response).first() is None
        assert sqlalchemy_auth_session.query(Request).first() is None
