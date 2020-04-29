from logging import Logger
from typing import Dict, TypedDict

from marshmallow import EXCLUDE, Schema, fields, post_load
from sqlalchemy import engine, orm

from .log import LoggerConfig, LoggerSchema


class SQLAlchemyEngineConfig(TypedDict, total=False):
    name_or_url: str
    echo: bool
    echo_pool: bool
    encoding: str
    implicit_returning: bool
    isolation_level: str
    logging_name: str
    pool_logging_name: str
    max_overflow: int
    pool_pre_ping: bool
    pool_size: int
    pool_recycle: int
    pool_reset_on_return: str
    pool_timeout: int
    strategy: str


class SQLAlchemyStorageConfig(TypedDict):
    bind: SQLAlchemyEngineConfig
    logger: LoggerConfig


class SQLAlchemyStorage:

    __slots__ = (
        "_bind",
        "_scoped_session",
        "_logger",
    )

    def __init__(self, bind: engine.Engine, logger: Logger):
        self._bind = bind
        self._logger = logger

        session_factory = orm.sessionmaker(bind)
        self._scoped_session = orm.scoped_session(session_factory)

    def setup(self) -> None:
        self._bind.connect()
        self._logger.info("DB initialized")

    def cleanup(self) -> None:
        self._scoped_session.remove()
        self._bind.dispose()
        self._logger.info("DB disposed")

    def get_session(self) -> orm.Session:
        return self._scoped_session()

    def remove_session(self) -> None:
        self._scoped_session.remove()

    @classmethod
    def from_config(cls, config: SQLAlchemyStorageConfig):
        return SQLAlchemyStorageSchema().load(config)


class SQLAlchemyEngineSchema(Schema):
    name_or_url = fields.Str(required=True)
    echo = fields.Bool(missing=False)
    echo_pool = fields.Bool(missing=False)
    encoding = fields.Str(missing="utf-8")
    implicit_returning = fields.Bool(missing=True)
    isolation_level = fields.Str(required=False)
    logging_name = fields.Str(missing="sqlalchemy.engine")
    pool_logging_name = fields.Str(missing="sqlalchemy.pool")
    max_overflow = fields.Int(missing=10)
    pool_pre_ping = fields.Bool(missing=False)
    pool_size = fields.Int(missing=5)
    pool_recycle = fields.Int(missing=3600)
    pool_reset_on_return = fields.Str(missing="rollback")
    pool_timeout = fields.Int(missing=30)
    strategy = fields.Str(required=False)

    class Meta:
        unknown = EXCLUDE

    @post_load
    def make_engine(self, data: Dict, **kwargs) -> engine.Engine:
        return engine.create_engine(**data)


class SQLAlchemyStorageSchema(Schema):
    bind = fields.Nested(SQLAlchemyEngineSchema, required=True)
    logger = fields.Nested(LoggerSchema, required=True)

    class Meta:
        unknown = EXCLUDE

    @post_load
    def make_service(self, data: Dict, **kwargs) -> SQLAlchemyStorage:
        return SQLAlchemyStorage(**data)
