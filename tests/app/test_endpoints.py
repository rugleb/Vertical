from datetime import date
from http import HTTPStatus
from typing import Callable, Dict

import pytest
from factory import Factory
from sqlalchemy.orm import Session
from starlette.applications import Starlette
from starlette.testclient import TestClient

from vertical import hdrs
from vertical.app import auth, hunter
from vertical.app.auth import Contract, Request, Response

APPLICATION_JSON = "application/json"


class TestPingEndpoint:
    path = "/ping"

    def test_that_route_is_named(self, client: TestClient) -> None:
        app: Starlette = client.app  # type: ignore

        url = app.url_path_for(name="ping")
        assert self.path == url

    def test_that_response_is_pong(
            self,
            client: TestClient,
            create_request_id: Callable,
            sqlalchemy_auth_session: Session,
    ) -> None:
        request_id = create_request_id()

        headers = {
            hdrs.X_REQUEST_ID: request_id,
            hdrs.CONTENT_TYPE: APPLICATION_JSON,
        }

        r = client.get(self.path, headers=headers)

        http_status = HTTPStatus.OK
        assert r.status_code == http_status

        assert r.json() == {
            "message": "pong",
            "data": {},
        }

        assert r.headers[hdrs.X_REQUEST_ID] == request_id

        assert sqlalchemy_auth_session.query(Request).first() is None
        assert sqlalchemy_auth_session.query(Response).first() is None


class TestPhoneReliabilityEndpoint:
    path = "/reliability/phone"

    def test_request_without_authorization_header(
            self,
            client: TestClient,
            create_request_id: Callable,
            sqlalchemy_auth_session: Session,
    ) -> None:
        request_id = create_request_id()

        headers = {
            hdrs.X_REQUEST_ID: request_id,
            hdrs.CONTENT_TYPE: APPLICATION_JSON,
        }

        r = client.post(self.path, headers=headers)

        http_status = HTTPStatus.UNAUTHORIZED
        assert r.status_code == http_status

        assert r.json() == {
            "message": "Authorization header not recognized",
        }

        assert r.headers[hdrs.X_REQUEST_ID] == request_id

        response = sqlalchemy_auth_session.query(Response).first()
        assert isinstance(response, Response)

        assert response.id == request_id
        assert response.body == r.json()
        assert response.code == r.status_code

        assert response.request.id == request_id
        assert response.request.path == r.request.path_url
        assert response.request.method == r.request.method
        assert response.request.body == r.request.body
        assert response.request.remote == "testclient:50000"

    def test_request_with_invalid_auth_scheme(
            self,
            client: TestClient,
            create_request_id: Callable,
            sqlalchemy_auth_session: Session,
    ) -> None:
        request_id = create_request_id()

        headers = {
            hdrs.X_REQUEST_ID: request_id,
            hdrs.CONTENT_TYPE: APPLICATION_JSON,
            hdrs.AUTHORIZATION: hdrs.BEARER,
        }

        r = client.post(self.path, headers=headers)

        http_status = HTTPStatus.UNAUTHORIZED
        assert r.status_code == http_status

        assert r.json() == {
            "message": "Invalid authorization scheme",
        }

        assert r.headers[hdrs.X_REQUEST_ID] == request_id

        response = sqlalchemy_auth_session.query(Response).first()
        assert isinstance(response, Response)

        assert response.id == request_id
        assert response.body == r.json()
        assert response.code == r.status_code

        assert response.request.id == request_id
        assert response.request.path == r.request.path_url
        assert response.request.method == r.request.method
        assert response.request.body == r.request.body
        assert response.request.remote == "testclient:50000"

    def test_request_with_invalid_token_type(
            self,
            client: TestClient,
            create_request_id: Callable,
            allowed_contract: auth.Contract,
            sqlalchemy_auth_session: Session,
    ) -> None:
        token = allowed_contract.token

        request_id = create_request_id()

        headers = {
            hdrs.X_REQUEST_ID: request_id,
            hdrs.CONTENT_TYPE: APPLICATION_JSON,
            hdrs.AUTHORIZATION: f"{hdrs.BASIC} {token}"
        }

        r = client.post(self.path, headers=headers)

        http_status = HTTPStatus.UNAUTHORIZED
        assert r.status_code == http_status

        assert r.json() == {
            "message": "Expected Bearer token type",
        }

        assert r.headers[hdrs.X_REQUEST_ID] == request_id

        response = sqlalchemy_auth_session.query(Response).first()
        assert isinstance(response, Response)

        assert response.id == request_id
        assert response.body == r.json()
        assert response.code == r.status_code

        assert response.request.id == request_id
        assert response.request.path == r.request.path_url
        assert response.request.method == r.request.method
        assert response.request.body == r.request.body
        assert response.request.remote == "testclient:50000"

    def test_request_with_invalid_access_token(
            self,
            client: TestClient,
            create_request_id: Callable,
            sqlalchemy_auth_session: Session,
    ) -> None:
        request_id = create_request_id()

        headers = {
            hdrs.X_REQUEST_ID: request_id,
            hdrs.CONTENT_TYPE: APPLICATION_JSON,
            hdrs.AUTHORIZATION: f"{hdrs.BEARER} TOKEN"
        }

        r = client.post(self.path, headers=headers)

        http_status = HTTPStatus.UNAUTHORIZED
        assert r.status_code == http_status

        assert r.json() == {
            "message": "Invalid access token",
        }

        assert r.headers[hdrs.X_REQUEST_ID] == request_id

        response = sqlalchemy_auth_session.query(Response).first()
        assert isinstance(response, Response)

        assert response.id == request_id
        assert response.body == r.json()
        assert response.code == r.status_code

        assert response.request.id == request_id
        assert response.request.path == r.request.path_url
        assert response.request.method == r.request.method
        assert response.request.body == r.request.body
        assert response.request.remote == "testclient:50000"

    def test_request_with_expired_contract(
            self,
            client: TestClient,
            create_request_id: Callable,
            sqlalchemy_auth_session: Session,
            expired_contract: auth.Contract,
    ) -> None:
        token = expired_contract.token

        request_id = create_request_id()

        headers = {
            hdrs.X_REQUEST_ID: request_id,
            hdrs.CONTENT_TYPE: APPLICATION_JSON,
            hdrs.AUTHORIZATION: f"{hdrs.BEARER} {token}"
        }

        r = client.post(self.path, headers=headers)

        http_status = HTTPStatus.UNAUTHORIZED
        assert r.status_code == http_status

        message = auth.ContractExpired(expired_contract).render()

        assert r.json() == {
            "message": message,
        }

        assert r.headers[hdrs.X_REQUEST_ID] == request_id

        response = sqlalchemy_auth_session.query(Response).first()
        assert isinstance(response, Response)

        assert response.id == request_id
        assert response.body == r.json()
        assert response.code == r.status_code

        assert response.request.id == request_id
        assert response.request.path == r.request.path_url
        assert response.request.method == r.request.method
        assert response.request.body == r.request.body
        assert response.request.remote == "testclient:50000"

    def test_request_with_revoked_contract(
            self,
            client: TestClient,
            create_request_id: Callable,
            sqlalchemy_auth_session: Session,
            revoked_contract: auth.Contract,
    ) -> None:
        token = revoked_contract.token

        request_id = create_request_id()

        headers = {
            hdrs.X_REQUEST_ID: request_id,
            hdrs.CONTENT_TYPE: APPLICATION_JSON,
            hdrs.AUTHORIZATION: f"{hdrs.BEARER} {token}"
        }

        r = client.post(self.path, headers=headers)

        http_status = HTTPStatus.UNAUTHORIZED
        assert r.status_code == http_status

        message = auth.ContractRevoked(revoked_contract).render()

        assert r.json() == {
            "message": message,
        }

        assert r.headers[hdrs.X_REQUEST_ID] == request_id

        response = sqlalchemy_auth_session.query(Response).first()
        assert isinstance(response, Response)

        assert response.id == request_id
        assert response.body == r.json()
        assert response.code == r.status_code

        assert response.request.id == request_id
        assert response.request.path == r.request.path_url
        assert response.request.method == r.request.method
        assert response.request.body == r.request.body
        assert response.request.remote == "testclient:50000"

    @pytest.mark.parametrize("json", [
        None,
        {},
    ])
    def test_request_without_invalid_json(
            self,
            client: TestClient,
            create_request_id: Callable,
            sqlalchemy_auth_session: Session,
            allowed_contract: Contract,
            json: Dict,
    ) -> None:
        token = allowed_contract.token

        request_id = create_request_id()

        headers = {
            hdrs.X_REQUEST_ID: request_id,
            hdrs.CONTENT_TYPE: APPLICATION_JSON,
            hdrs.AUTHORIZATION: f"{hdrs.BEARER} {token}"
        }

        r = client.post(self.path, json=json, headers=headers)

        http_status = HTTPStatus.UNPROCESSABLE_ENTITY
        assert r.status_code == http_status

        assert r.json() == {
            "message": "Input payload validation failed",
            "errors": {
                "number": [
                    "Missing data for required field.",
                ],
            },
        }

        assert r.headers[hdrs.X_REQUEST_ID] == request_id

        response = sqlalchemy_auth_session.query(Response).first()
        assert isinstance(response, Response)

        assert response.id == request_id
        assert response.body == r.json()
        assert response.code == r.status_code

        assert response.request.id == request_id
        assert response.request.path == r.request.path_url
        assert response.request.method == r.request.method
        assert response.request.body == json
        assert response.request.remote == "testclient:50000"

    @pytest.mark.parametrize("number", [
        "7000000000",
        "80000000000",
        "700000000000",
        "phone",
        "",
    ])
    def test_request_with_invalid_phone_number_format(
            self,
            client: TestClient,
            create_request_id: Callable,
            sqlalchemy_auth_session: Session,
            allowed_contract: Contract,
            number: str,
    ) -> None:
        token = allowed_contract.token

        request_id = create_request_id()

        headers = {
            hdrs.X_REQUEST_ID: request_id,
            hdrs.CONTENT_TYPE: APPLICATION_JSON,
            hdrs.AUTHORIZATION: f"{hdrs.BEARER} {token}"
        }

        json = {
            "number": number,
        }

        r = client.post(self.path, json=json, headers=headers)

        http_status = HTTPStatus.UNPROCESSABLE_ENTITY
        assert r.status_code == http_status

        assert r.json() == {
            "message": "Input payload validation failed",
            "errors": {
                "number": [
                    "Phone number does't match expected pattern: 7\\d{10}.",
                ],
            },
        }

        assert r.headers[hdrs.X_REQUEST_ID] == request_id

        response = sqlalchemy_auth_session.query(Response).first()
        assert isinstance(response, Response)

        assert response.id == request_id
        assert response.body == r.json()
        assert response.code == r.status_code

        assert response.request.id == request_id
        assert response.request.path == r.request.path_url
        assert response.request.method == r.request.method
        assert response.request.body == json
        assert response.request.remote == "testclient:50000"

    def test_request_with_undefined_phone_number(
            self,
            client: TestClient,
            create_request_id: Callable,
            sqlalchemy_auth_session: Session,
            allowed_contract: Contract,
            phone_number_generator: Callable,
    ) -> None:
        token = allowed_contract.token

        request_id = create_request_id()

        headers = {
            hdrs.X_REQUEST_ID: request_id,
            hdrs.CONTENT_TYPE: APPLICATION_JSON,
            hdrs.AUTHORIZATION: f"{hdrs.BEARER} {token}"
        }

        json = {
            "number": phone_number_generator(),
        }

        r = client.post(self.path, json=json, headers=headers)

        http_status = HTTPStatus.OK
        assert r.status_code == http_status

        assert r.json() == {
            "message": "OK",
            "data": {
                "status": False,
                "period": None,
            },
        }

        assert r.headers[hdrs.X_REQUEST_ID] == request_id

        response = sqlalchemy_auth_session.query(Response).first()
        assert isinstance(response, Response)

        assert response.id == request_id
        assert response.body == r.json()
        assert response.code == r.status_code

        assert response.request.id == request_id
        assert response.request.path == r.request.path_url
        assert response.request.method == r.request.method
        assert response.request.body == json
        assert response.request.remote == "testclient:50000"

    def test_request_with_known_phone_number_no_hit(
            self,
            client: TestClient,
            sqlalchemy_auth_session: Session,
            allowed_contract: Contract,
            create_request_id: Callable,
            phone_number_generator: Callable,
            submission_factory: Factory,
    ) -> None:
        registered_at = date(2020, 1, 1)
        updated_at = date(2020, 5, 1)

        person_name_hash = hunter.make_hash("Jake")
        person_birthday_hash = hunter.make_hash("1970-01-01")

        phone_number = phone_number_generator()
        phone_number_hash = hunter.make_hash(phone_number)

        submission_factory.create(
            id=1,
            date=registered_at,
            phone_number_hash=phone_number_hash,
            person_name_hash=person_name_hash,
            person_birthday_hash=person_birthday_hash,
        )

        submission_factory.create(
            id=2,
            date=updated_at,
            phone_number_hash=phone_number_hash,
            person_name_hash=person_name_hash,
            person_birthday_hash=person_birthday_hash,
        )

        token = allowed_contract.token

        request_id = create_request_id()

        headers = {
            hdrs.X_REQUEST_ID: request_id,
            hdrs.CONTENT_TYPE: APPLICATION_JSON,
            hdrs.AUTHORIZATION: f"{hdrs.BEARER} {token}"
        }

        json = {
            "number": phone_number,
        }

        r = client.post(self.path, json=json, headers=headers)

        http_status = HTTPStatus.OK
        assert r.status_code == http_status

        assert r.json() == {
            "message": "OK",
            "data": {
                "status": False,
                "period": {
                    "registered_at": "2020.01.01",
                    "updated_at": "2020.05.01",
                },
            },
        }

        assert r.headers[hdrs.X_REQUEST_ID] == request_id

        response = sqlalchemy_auth_session.query(Response).first()
        assert isinstance(response, Response)

        assert response.id == request_id
        assert response.body == r.json()
        assert response.code == r.status_code

        assert response.request.id == request_id
        assert response.request.path == r.request.path_url
        assert response.request.method == r.request.method
        assert response.request.body == json
        assert response.request.remote == "testclient:50000"

    def test_request_with_known_phone_number_hit(
            self,
            client: TestClient,
            sqlalchemy_auth_session: Session,
            allowed_contract: Contract,
            create_request_id: Callable,
            phone_number_generator: Callable,
            submission_factory: Factory,
    ) -> None:
        registered_at = date(2000, 1, 1)
        updated_at = date(2020, 1, 1)

        person_name_hash = hunter.make_hash("Jake")
        person_birthday_hash = hunter.make_hash("1970-01-01")

        phone_number = phone_number_generator()
        phone_number_hash = hunter.make_hash(phone_number)

        submission_factory.create(
            id=1,
            date=registered_at,
            phone_number_hash=phone_number_hash,
            person_name_hash=person_name_hash,
            person_birthday_hash=person_birthday_hash,
        )

        submission_factory.create(
            id=2,
            date=updated_at,
            phone_number_hash=phone_number_hash,
            person_name_hash=person_name_hash,
            person_birthday_hash=person_birthday_hash,
        )

        token = allowed_contract.token

        request_id = create_request_id()

        headers = {
            hdrs.X_REQUEST_ID: request_id,
            hdrs.CONTENT_TYPE: APPLICATION_JSON,
            hdrs.AUTHORIZATION: f"{hdrs.BEARER} {token}"
        }

        json = {
            "number": phone_number,
        }

        r = client.post(self.path, json=json, headers=headers)

        http_status = HTTPStatus.OK
        assert r.status_code == http_status

        assert r.json() == {
            "message": "OK",
            "data": {
                "status": True,
                "period": {
                    "registered_at": "2000.01.01",
                    "updated_at": "2020.01.01",
                },
            },
        }

        assert r.headers[hdrs.X_REQUEST_ID] == request_id

        response = sqlalchemy_auth_session.query(Response).first()
        assert isinstance(response, Response)

        assert response.id == request_id
        assert response.body == r.json()
        assert response.code == r.status_code

        assert response.request.id == request_id
        assert response.request.path == r.request.path_url
        assert response.request.method == r.request.method
        assert response.request.body == json
        assert response.request.remote == "testclient:50000"
