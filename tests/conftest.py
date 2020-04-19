import os
import secrets
import string
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Callable, Dict, Iterator, Type

import docker
import factory
import pytest
from alembic.command import downgrade, upgrade
from alembic.config import Config
from sqlalchemy import engine, exc, orm
from starlette.testclient import TestClient

from vertical import AppConfig, create_app, hdrs
from vertical.app import auth, hunter
from vertical.app.utils import unused_port

LOCALHOST = "127.0.0.1"

HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(HERE)

DEFAULT_POSTGRES_HOST = LOCALHOST
DEFAULT_POSTGRES_PORT = 5432
DEFAULT_POSTGRES_USER = "postgres"
DEFAULT_POSTGRES_PASSWORD = "postgres"
DEFAULT_POSTGRES_DATABASE = "postgres"


@contextmanager
def postgres_server(
        host: str = DEFAULT_POSTGRES_HOST,
        port: int = DEFAULT_POSTGRES_PORT,
        user: str = DEFAULT_POSTGRES_USER,
        password: str = DEFAULT_POSTGRES_PASSWORD,
        database: str = DEFAULT_POSTGRES_DATABASE,
) -> Iterator[Dict]:
    client = docker.from_env()

    container = client.containers.run(
        image="postgres:11-alpine",
        detach=True,
        environment={
            "POSTGRES_PASSWORD": password,
            "POSTGRES_USER": user,
            "POSTGRES_DB": database,
        },
        ports={
            "5432/tcp": (host, port),
        },
    )

    try:
        yield {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
        }
    finally:
        container.remove(force=True)
        client.close()


def establish_connection(bind: engine.Engine) -> engine.Engine:
    for _ in range(100):
        try:
            bind.connect()
            break
        except exc.OperationalError:
            time.sleep(0.05)
    return bind


@contextmanager
def sqlalchemy_bind(config: Dict) -> Iterator[engine.Engine]:
    url_template = "postgresql://{user}:{password}@{host}:{port}/{database}"
    url = url_template.format_map(config)
    bind = engine.create_engine(url)
    try:
        yield establish_connection(bind)
    finally:
        bind.dispose()


@contextmanager
def sqlalchemy_session(bind: engine.Engine) -> Iterator[orm.Session]:
    session_factory = orm.sessionmaker(bind)
    session = session_factory()
    try:
        yield session
    finally:
        session.cleanup()


@contextmanager
def run_migrations(path: str, bind: engine.Engine) -> Iterator:
    config = Config(path)

    url = str(bind.url)
    config.set_main_option("url", url)

    upgrade(config, "head")
    try:
        yield
    finally:
        downgrade(config, "base")


@pytest.fixture(scope="session")
def sqlalchemy_auth_bind() -> Iterator:
    host = LOCALHOST
    port = unused_port(host)
    with postgres_server(port=port) as url:
        with sqlalchemy_bind(url) as bind:
            yield bind


AuthSession = orm.scoped_session(orm.sessionmaker())
HunterSession = orm.scoped_session(orm.sessionmaker())


@pytest.fixture
def sqlalchemy_auth_session(sqlalchemy_auth_bind: engine.Engine) -> Iterator:
    alembic = os.path.join(ROOT, "alembic.ini")
    with run_migrations(alembic, sqlalchemy_auth_bind):
        AuthSession.configure(bind=sqlalchemy_auth_bind)
        try:
            yield AuthSession()
        finally:
            AuthSession.remove()


@pytest.fixture(scope="session")
def sqlalchemy_hunter_bind() -> Iterator:
    host = LOCALHOST
    port = unused_port(host)
    with postgres_server(port=port) as url:
        with sqlalchemy_bind(url) as bind:
            yield bind


@pytest.fixture
def sqlalchemy_hunter_session(sqlalchemy_hunter_bind: engine.Engine):
    meta = hunter.Model.metadata
    meta.create_all(sqlalchemy_hunter_bind)

    HunterSession.configure(bind=sqlalchemy_hunter_bind)
    try:
        yield HunterSession()
    finally:
        HunterSession.remove()
        meta.drop_all(sqlalchemy_hunter_bind)


@pytest.fixture
def config(
        sqlalchemy_auth_session: orm.Session,
        sqlalchemy_hunter_session: orm.Session,
) -> Iterator[AppConfig]:
    yield {
        "auth_service": {
            "pool": {
                "dsn": str(sqlalchemy_auth_session.bind.url),
            },
        },
        "hunter_db": {
            "bind": {
                "name_or_url": str(sqlalchemy_hunter_session.bind.url),
            },
        },
        "phone_service": {
            "delta": 180,
        }
    }


@pytest.fixture
def client(config: AppConfig) -> Iterator:
    app = create_app(config)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def create_uuid() -> str:
    uuid_obj = uuid.uuid4()
    return str(uuid_obj)


@pytest.fixture
def create_request_id() -> Callable:
    return create_uuid


@pytest.fixture
def headers(create_request_id: Callable) -> Dict:
    return {
        hdrs.X_REQUEST_ID: create_request_id(),
        hdrs.CONTENT_TYPE: "application/json",
    }


class AuthFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session = AuthSession
        sqlalchemy_session_persistence = "commit"


class ClientFactory(AuthFactory):
    class Meta:
        model = auth.Client

    id = factory.LazyFunction(create_uuid)
    name = factory.Faker("name")
    created_at = factory.LazyFunction(datetime.now)


class ContractFactory(AuthFactory):
    class Meta:
        model = auth.Contract

    id = factory.LazyFunction(create_uuid)
    client_id = None
    token = factory.LazyFunction(secrets.token_hex)
    created_at = factory.LazyFunction(datetime.now)
    expired_at = None
    revoked_at = None

    client = factory.SubFactory(ClientFactory)


@pytest.fixture
def expired_contract() -> auth.Contract:
    expired_at = datetime.now() - timedelta(365)
    contract = ContractFactory.create(expired_at=expired_at)
    assert contract.is_expired()
    return contract


@pytest.fixture
def revoked_contract() -> auth.Contract:
    revoked_at = datetime.now() - timedelta(365)
    contract = ContractFactory.create(revoked_at=revoked_at)
    assert contract.is_revoked()
    return contract


@pytest.fixture
def allowed_contract() -> auth.Contract:
    contract = ContractFactory.create()
    assert not contract.is_expired()
    assert not contract.is_revoked()
    return contract


def generate_phone_number():
    choice = secrets.SystemRandom().choice
    return "7" + "".join(choice(string.digits) for _ in range(10))


@pytest.fixture
def phone_number_generator() -> Callable:
    return generate_phone_number


class HunterFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session = HunterSession
        sqlalchemy_session_persistence = "commit"


class SubmissionFactory(HunterFactory):
    class Meta:
        model = hunter.Submission

    id = factory.Sequence(lambda n: n)
    date = factory.LazyFunction(datetime.now)
    phone_number_hash = None
    person_name_hash = None
    person_birthday_hash = None


@pytest.fixture
def submission_factory() -> Type:
    return SubmissionFactory
