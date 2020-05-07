from typing import Dict, TypedDict

from marshmallow import EXCLUDE, Schema, fields, post_load
from sqlalchemy import engine


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


class SQLAlchemyEngineSchema(Schema):
    name_or_url = fields.Str(required=True)
    echo = fields.Bool(missing=False)
    echo_pool = fields.Bool(missing=False)
    max_overflow = fields.Int(missing=10)
    pool_pre_ping = fields.Bool(missing=False)
    pool_size = fields.Int(missing=5)
    pool_recycle = fields.Int(missing=3600)
    pool_timeout = fields.Int(missing=30)

    class Meta:
        unknown = EXCLUDE

    @post_load
    def make_engine(self, data: Dict, **kwargs) -> engine.Engine:
        return engine.create_engine(**data)
