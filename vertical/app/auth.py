from http import HTTPStatus
from typing import Dict, Optional, TypedDict
from uuid import UUID

from asyncpg.pool import Pool, create_pool
from marshmallow import EXCLUDE, Schema, fields, post_load
from sqlalchemy import Column, ForeignKey, orm
from sqlalchemy.dialects import postgresql as pgsql
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base

from vertical import hdrs

from .protocols import RequestProtocol, ResponseProtocol
from .utils import now

DATETIME_FORMAT = "%Y.%m.%d %H:%M:%S"


Model: DeclarativeMeta = declarative_base()


class Client(Model):
    __tablename__ = "clients"

    id = Column("client_id", pgsql.UUID, primary_key=True)
    name = Column(pgsql.VARCHAR)
    created_at = Column(pgsql.TIMESTAMP)


class Contract(Model):
    __tablename__ = "contracts"

    id = Column("contract_id", pgsql.UUID, primary_key=True)
    client_id = Column(pgsql.UUID, ForeignKey(Client.id))
    token = Column(pgsql.VARCHAR)
    created_at = Column(pgsql.TIMESTAMP)
    expired_at = Column(pgsql.TIMESTAMP)
    revoked_at = Column(pgsql.TIMESTAMP)

    client = orm.relationship(Client)

    def is_expired(self) -> bool:
        if self.expired_at is None or self.expired_at > now():
            return False
        return True

    def is_revoked(self) -> bool:
        if self.revoked_at is None or self.revoked_at > now():
            return False
        return True


class Request(Model):
    __tablename__ = "requests"

    id = Column("request_id", pgsql.UUID, primary_key=True)
    remote = Column(pgsql.VARCHAR)
    method = Column(pgsql.VARCHAR)
    path = Column(pgsql.VARCHAR)
    body = Column(pgsql.JSONB)
    created_at = Column(pgsql.TIMESTAMP)


class Response(Model):
    __tablename__ = "responses"

    id = Column("request_id", None, ForeignKey(Request.id), primary_key=True)
    body = Column(pgsql.JSONB)
    code = Column(pgsql.SMALLINT)
    created_at = Column(pgsql.TIMESTAMP)

    request = orm.relationship(Request)


class Identification(Model):
    __tablename__ = "identifications"

    id = Column("identification_id", pgsql.UUID, primary_key=True)
    request_id = Column(None, ForeignKey(Request.id))
    contract_id = Column(None, ForeignKey(Contract.id))

    request = orm.relationship(Request)
    contract = orm.relationship(Contract)


class AuthException(Exception):
    http_status = HTTPStatus.UNAUTHORIZED

    def render(self) -> str:
        raise NotImplementedError()


class AuthHeaderNotRecognized(AuthException):

    def render(self) -> str:
        return "Authorization header not recognized"


class InvalidAuthScheme(AuthException):

    def render(self) -> str:
        return "Invalid authorization scheme"


class BearerExpected(AuthException):

    def render(self) -> str:
        return "Expected Bearer token type"


class InvalidAccessToken(AuthException):

    def render(self) -> str:
        return "Invalid access token"


class ContractUnavailable(AuthException):

    def __init__(self, contract: Contract):
        self.contract = contract

    def render(self) -> str:
        raise NotImplementedError()


class ContractExpired(ContractUnavailable):

    def render(self) -> str:
        expired_at = self.contract.expired_at.strftime(DATETIME_FORMAT)

        return f"Your contract was expired on {expired_at}"


class ContractRevoked(ContractUnavailable):

    def render(self) -> str:
        revoked_at = self.contract.revoked_at.strftime(DATETIME_FORMAT)

        return f"Your contract was revoked on {revoked_at}"


class AsyncpgPoolConfig(TypedDict, total=False):
    dsn: str
    min_size: str
    max_size: str
    max_queries: str
    max_inactive_connection_lifetime: float
    timeout: float
    command_timeout: float
    statement_cache_size: int
    max_cached_statement_lifetime: float


class AuthServiceConfig(TypedDict):
    pool: AsyncpgPoolConfig


class AuthService:

    __slots__ = (
        "_pool",
    )

    def __init__(self, pool: Pool):
        self._pool = pool

    async def setup(self) -> None:
        await self._pool

    async def cleanup(self) -> None:
        await self._pool.close()

    async def ping(self) -> bool:
        return await self._pool.fetchval("SELECT TRUE;")

    async def save_request(self, request: RequestProtocol) -> Request:
        query = """
            INSERT INTO requests
                (request_id, remote, method, path, body)
            VALUES
                ($1::UUID, $2::VARCHAR, $3::VARCHAR, $4::VARCHAR, $5::JSONB)
            RETURNING
                requests.request_id AS id
                , requests.remote
                , requests.method
                , requests.path
                , requests.body
            ;
        """

        record = await self._pool.fetchrow(
            query,
            request.identifier,
            request.remote_addr,
            request.method,
            request.path,
            request.body,
        )

        return Request(**record)

    async def save_response(self, response: ResponseProtocol) -> Response:
        query = """
            INSERT INTO responses
                (request_id, code, body)
            VALUES
                ($1::UUID, $2::SMALLINT, $3::JSONB)
            RETURNING
                responses.request_id AS id
                , responses.code
                , responses.body
            ;
        """

        record = await self._pool.fetchrow(
            query,
            response.request.identifier,
            response.code,
            response.body,
        )

        return Response(**record)

    async def get_contract_by_token(self, token: str) -> Optional[Contract]:
        query = """
            SELECT
                contracts.contract_id AS id
                , contracts.client_id
                , contracts.token
                , contracts.created_at
                , contracts.expired_at
                , contracts.revoked_at
            FROM contracts WHERE token = $1::VARCHAR LIMIT 1;
        """

        record = await self._pool.fetchrow(query, token)
        if not record:
            return None
        return Contract(**record)

    async def identify(self, request_id: UUID, contract_id: UUID):
        query = """
            INSERT INTO identifications
                (request_id, contract_id)
            VALUES
                ($1::UUID, $2::UUID)
            RETURNING
                identifications.identification_id AS id
                , identifications.request_id
                , identifications.contract_id
            ;
        """

        record = await self._pool.fetchrow(query, request_id, contract_id)
        return Identification(**record)

    async def authorize(self, request: RequestProtocol) -> Identification:
        if not request.authorization:
            raise AuthHeaderNotRecognized()

        try:
            scheme, token = request.authorization.split()
        except ValueError:
            raise InvalidAuthScheme()

        if scheme != hdrs.BEARER:
            raise BearerExpected()

        contract = await self.get_contract_by_token(token)

        if not contract:
            raise InvalidAccessToken()

        if contract.is_expired():
            raise ContractExpired(contract)

        if contract.is_revoked():
            raise ContractRevoked(contract)

        request_id = UUID(request.identifier)
        return await self.identify(request_id, contract.id)

    @classmethod
    def from_config(cls, config: AuthServiceConfig) -> "AuthService":
        return AuthServiceSchema().load(config)


class AsyncpgPoolSchema(Schema):
    dsn = fields.Str(required=True)
    min_size = fields.Int(missing=0)
    max_size = fields.Int(missing=10)
    max_queries = fields.Int(missing=1000)
    max_inactive_connection_lifetime = fields.Int(missing=3600)
    timeout = fields.Float(missing=10)
    command_timeout = fields.Float(missing=10)
    statement_cache_size = fields.Int(missing=1024)
    max_cached_statement_lifetime = fields.Int(missing=3600)

    class Meta:
        unknown = EXCLUDE

    @post_load
    def make_pool(self, data: Dict, **kwargs) -> Pool:
        return create_pool(**data)


class AuthServiceSchema(Schema):
    pool = fields.Nested(AsyncpgPoolSchema, required=True)

    class Meta:
        unknown = EXCLUDE

    @post_load
    def make_service(self, data: Dict, **kwargs) -> AuthService:
        return AuthService(**data)
