import asyncio
import logging
import time
from datetime import date
from typing import Dict, Final, Optional, TypedDict

import attr
import sqlalchemy as sa
from marshmallow import EXCLUDE, Schema, fields, post_load
from pygost import gost341194
from starlette.concurrency import run_in_threadpool

from .alchemy import SQLAlchemyEngineConfig, SQLAlchemyEngineSchema
from .log import LoggerConfig, LoggerSchema

__all__ = (
    "Period",
    "PeriodSchema",
    "Reliability",
    "ReliabilitySchema",
    "make_hash",
    "HunterServiceConfig",
    "HunterService",
    "HunterServiceSchema",
)

DATE_FORMAT: Final = "%Y.%m.%d"


@attr.s(slots=True, frozen=True)
class Period:
    registered_at: date = attr.ib()
    updated_at: date = attr.ib()


class PeriodSchema(Schema):
    registered_at = fields.Date(DATE_FORMAT, required=True)
    updated_at = fields.Date(DATE_FORMAT, required=True)


@attr.s(slots=True, frozen=True)
class Reliability:
    status: bool = attr.ib()
    period: Optional[Period] = attr.ib()

    def to_dict(self) -> Dict:
        return ReliabilitySchema().dump(self)


class ReliabilitySchema(Schema):
    status = fields.Bool(required=True)
    period = fields.Nested(PeriodSchema, allow_none=True, required=True)


def make_hash(data: str) -> str:
    binary = data.encode()
    hashed = gost341194.PBKDF2_HASHER(binary)
    return hashed.hexdigest().upper()


class HunterServiceConfig(TypedDict):
    bind: SQLAlchemyEngineConfig
    days: int
    schema: str
    table: str
    timeout: float
    logger: LoggerConfig


class HunterException(Exception):
    pass


class HunterService:

    __slots__ = (
        "_days",
        "_bind",
        "_metadata",
        "_submissions",
        "_hash_factory",
        "_timeout",
        "_logger",
    )

    def __init__(
        self,
        days: int,
        bind: sa.engine.Engine,
        schema: str,
        table: str,
        timeout: float,
        logger: logging.Logger,
    ):
        self._days = days
        self._bind = bind
        self._metadata = sa.MetaData(bind=bind, schema=schema)
        self._timeout = timeout
        self._logger = logger

        self._submissions = sa.Table(
            table,
            self._metadata,
            sa.Column("sub_no", sa.VARCHAR(10), primary_key=True),
            sa.Column("creation_datetime", sa.DATE(), nullable=False),
            sa.Column("tel", sa.VARCHAR(64), nullable=False),
            sa.Column("phk1", sa.VARCHAR(64), nullable=False),
            sa.Column("dob", sa.VARCHAR(64), nullable=False),
        )

        self._hash_factory = make_hash

    def setup(self) -> None:
        self._bind.connect()

        schema = self._metadata.schema
        self._logger.info("Connected to Hunter '%s' schema", schema)

    def cleanup(self) -> None:
        self._bind.dispose()

    def make_hash(self, data: str) -> str:
        return self._hash_factory(data)

    def metadata(self) -> sa.MetaData:
        return self._metadata

    def submissions(self) -> sa.Table:
        return self._submissions

    def get_period(self, phone_hash: str) -> Optional[Period]:
        submissions = self.submissions()

        registered_at = sa.func.min(submissions.c.creation_datetime)
        updated_at = sa.func.max(submissions.c.creation_datetime)

        columns = (
            registered_at.label("registered_at"),
            updated_at.label("updated_at"),
        )

        query = sa.select(columns).where(submissions.c.tel == phone_hash)
        registered_at, updated_at = self._bind.execute(query).fetchone()

        if registered_at is not None:
            return Period(registered_at, updated_at)
        return None

    def get_status(self, phone_hash: str) -> bool:
        submissions = self.submissions()

        registered_at = sa.func.min(submissions.c.creation_datetime)
        updated_at = sa.func.max(submissions.c.creation_datetime)

        delta = (updated_at - registered_at).label("delta")

        deltas = sa.select(
            [delta]
        ).where(
            submissions.c.tel == phone_hash,
        ).group_by(
            submissions.c.tel,
            submissions.c.phk1,
            submissions.c.dob,
        ).alias("deltas")

        query = sa.select(
            [deltas.c.delta]
        ).where(
            deltas.c.delta > self._days
        ).limit(1)

        return self._bind.execute(query).scalar() is not None

    async def verify(self, phone_number: str) -> Reliability:
        phone_hash = self.make_hash(phone_number)

        gather = asyncio.gather(
            run_in_threadpool(self.get_status, phone_hash),
            run_in_threadpool(self.get_period, phone_hash),
        )

        self._logger.info("Started reliability query")
        started_at = time.perf_counter()

        try:
            status, period = await asyncio.wait_for(
                gather,
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            self._logger.warning("Query timeout is up")
            raise HunterException("Hunted query exceeded the given timeout")
        else:
            return Reliability(status=status, period=period)
        finally:
            elapsed = time.perf_counter() - started_at
            self._logger.info("Query execution time: %.4f ms", elapsed)

    @classmethod
    def from_config(cls, config: HunterServiceConfig) -> "HunterService":
        return HunterServiceSchema().load(config)


class HunterServiceSchema(Schema):
    days = fields.Int(required=True)
    bind = fields.Nested(SQLAlchemyEngineSchema, required=True)
    schema = fields.Str(required=True)
    table = fields.Str(required=True)
    timeout = fields.Float(required=True)
    logger = fields.Nested(LoggerSchema, required=True)

    class Meta:
        unknown = EXCLUDE

    @post_load
    def release(self, data: Dict, **kwargs) -> HunterService:
        return HunterService(**data)
