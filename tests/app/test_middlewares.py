from http import HTTPStatus

from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vertical import hdrs
from vertical.app import auth, utils

APPLICATION_JSON = "application/json"


class TestContentTypeMiddleware:
    url = "/ping"

    def test_request_without_content_type(
            self,
            client: TestClient,
            sqlalchemy_auth_session: Session,
    ) -> None:
        response = client.get(self.url)

        http_status = HTTPStatus.BAD_REQUEST
        assert response.status_code == http_status

        assert response.json() == {
            "message": "Content-Type header not recognized",
        }

        request_id = response.headers[hdrs.X_REQUEST_ID]
        assert utils.is_valid_uuid(request_id)

        assert sqlalchemy_auth_session.query(auth.Request).first() is None
        assert sqlalchemy_auth_session.query(auth.Response).first() is None

    def test_request_without_invalid_content_type(
            self,
            client: TestClient,
            sqlalchemy_auth_session: Session,
    ) -> None:
        headers = {
            hdrs.CONTENT_TYPE: "application/html",
        }

        response = client.get(self.url, headers=headers)

        http_status = HTTPStatus.UNSUPPORTED_MEDIA_TYPE
        assert response.status_code == http_status

        assert response.json() == {
            "message": "Unsupported media type",
        }

        request_id = response.headers[hdrs.X_REQUEST_ID]
        assert utils.is_valid_uuid(request_id)

        assert sqlalchemy_auth_session.query(auth.Request).first() is None
        assert sqlalchemy_auth_session.query(auth.Response).first() is None


class TestJsonDecoderMiddleware:
    url = "/ping"

    def test_request_without_body(
            self,
            client: TestClient,
            sqlalchemy_auth_session: Session,
    ) -> None:
        headers = {
            hdrs.CONTENT_TYPE: APPLICATION_JSON,
        }

        response = client.get(self.url, headers=headers)

        http_status = HTTPStatus.OK
        assert response.status_code == http_status

        assert response.json() == {
            "message": "pong",
            "data": {},
        }

        request_id = response.headers[hdrs.X_REQUEST_ID]
        assert utils.is_valid_uuid(request_id)

        assert sqlalchemy_auth_session.query(auth.Request).first() is None
        assert sqlalchemy_auth_session.query(auth.Response).first() is None

    def test_request_with_invalid_json_body(
            self,
            client: TestClient,
            sqlalchemy_auth_session: Session,
    ) -> None:
        headers = {
            hdrs.CONTENT_TYPE: APPLICATION_JSON,
        }

        data = "{key:value}"
        response = client.post(self.url, headers=headers, data=data)

        http_status = HTTPStatus.BAD_REQUEST
        assert response.status_code == http_status

        assert response.json() == {
            "message": "Could not parse request body",
        }

        request_id = response.headers[hdrs.X_REQUEST_ID]
        assert utils.is_valid_uuid(request_id)

        assert sqlalchemy_auth_session.query(auth.Request).first() is None
        assert sqlalchemy_auth_session.query(auth.Response).first() is None
