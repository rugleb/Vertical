import os
import secrets
import string
import time
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from typing import Callable, Dict, Iterator

import docker
import factory
import pytest
import sqlalchemy as sa
from alembic.command import downgrade, upgrade
from alembic.config import Config
from sqlalchemy import exc, orm
from starlette.applications import Starlette
from starlette.testclient import TestClient

from vertical.app import AppConfig, auth, create_app, hunter, utils

HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(HERE)

DEFAULT_POSTGRES_HOST = utils.LOCALHOST
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


def establish_connection(bind: sa.engine.Engine) -> sa.engine.Engine:
    for _ in range(100):
        try:
            bind.connect()
            break
        except exc.OperationalError:
            time.sleep(0.05)
    return bind


@contextmanager
def sqlalchemy_bind(config: Dict) -> Iterator[sa.engine.Engine]:
    url_template = "postgresql://{user}:{password}@{host}:{port}/{database}"
    url = url_template.format_map(config)
    bind = sa.engine.create_engine(url)
    try:
        yield establish_connection(bind)
    finally:
        bind.dispose()


@contextmanager
def sqlalchemy_session(bind: sa.engine.Engine) -> Iterator[orm.Session]:
    session_factory = orm.sessionmaker(bind)
    session = session_factory()
    try:
        yield session
    finally:
        session.cleanup()


@contextmanager
def run_migrations(path: str, bind: sa.engine.Engine) -> Iterator:
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
    host = utils.LOCALHOST
    port = utils.unused_port(host)
    with postgres_server(port=port) as url:
        with sqlalchemy_bind(url) as bind:
            yield bind


AuthSession = orm.scoped_session(orm.sessionmaker())


@pytest.fixture
def sqlalchemy_auth_session(sqlalchemy_auth_bind: sa.engine.Engine):
    alembic = os.path.join(ROOT, "alembic.ini")
    with run_migrations(alembic, sqlalchemy_auth_bind):
        AuthSession.configure(bind=sqlalchemy_auth_bind)
        try:
            yield AuthSession()
        finally:
            AuthSession.remove()


@pytest.fixture(scope="session")
def sqlalchemy_hunter_bind() -> Iterator:
    host = utils.LOCALHOST
    port = utils.unused_port(host)
    with postgres_server(port=port) as url:
        with sqlalchemy_bind(url) as bind:
            yield bind


@pytest.fixture
def sqlalchemy_hunter_session(
    sqlalchemy_hunter_bind: sa.engine.Engine,
    app: Starlette,
):
    meta = app.state.hunter_service.metadata()

    sqlalchemy_hunter_bind.execute("CREATE SCHEMA " + meta.schema)
    meta.create_all(sqlalchemy_hunter_bind)

    try:
        yield sqlalchemy_hunter_bind
    finally:
        meta.drop_all(sqlalchemy_hunter_bind)
        sqlalchemy_hunter_bind.execute("DROP SCHEMA " + meta.schema)


@pytest.fixture
def hunter_config(sqlalchemy_hunter_bind: sa.engine.Engine) -> Dict:
    return {
        "bind": {
            "name_or_url": str(sqlalchemy_hunter_bind.url),
        },
        "days": 180,
        "schema": "yavert",
        "table": "hundata",
        "logger": {
            "name": "hunter",
        },
        "timeout": 10,
    }


@pytest.fixture
def auth_config(sqlalchemy_auth_session: orm.Session) -> Dict:
    return {
        "pool": {
            "dsn": str(sqlalchemy_auth_session.bind.url),
        },
        "logger": {
            "name": "audit",
        },
    }


@pytest.fixture
def config(
    auth_config: auth.AuthServiceConfig,
    hunter_config: hunter.HunterServiceConfig,
) -> Iterator[AppConfig]:
    yield {
        "auth_service": auth_config,
        "hunter_service": hunter_config,
    }


@pytest.fixture
def app(config: AppConfig) -> Starlette:
    return create_app(config)


@pytest.fixture
def client(app: Starlette, sqlalchemy_hunter_session) -> Iterator:
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def submission_factory(
    submission_number: int,
    submission_created_at: date,
    person_name: str,
    person_birthday: str,
    person_phone_number: str,
) -> Dict:
    person_name_hash = hunter.make_hash(person_name)
    person_birthday_hash = hunter.make_hash(person_birthday)
    person_phone_number_hash = hunter.make_hash(person_phone_number)

    return {
        "sub_no": submission_number,
        "creation_datetime": submission_created_at,
        "phk1": person_name_hash,
        "tel": person_phone_number_hash,
        "dob": person_birthday_hash,
    }


@pytest.fixture
def create_submission(
    sqlalchemy_hunter_session: sa.engine.Engine,
    app: Starlette,
) -> Callable:
    table = app.state.hunter_service.submissions()

    def f(**kwargs):
        values = submission_factory(**kwargs)
        query = table.insert().values(**values)
        return sqlalchemy_hunter_session.execute(query)

    return f


def generate_uuid() -> str:
    uuid_obj = uuid.uuid4()
    return str(uuid_obj)


@pytest.fixture
def request_id_generator() -> Callable:
    return utils.make_request_id


class AuthFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session = AuthSession
        sqlalchemy_session_persistence = "commit"


class ClientFactory(AuthFactory):
    class Meta:
        model = auth.Client

    id = factory.LazyFunction(generate_uuid)
    name = factory.Faker("name")
    created_at = factory.LazyFunction(datetime.now)


class ContractFactory(AuthFactory):
    class Meta:
        model = auth.Contract

    id = factory.LazyFunction(generate_uuid)
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
