from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Optional, Protocol, TypedDict

import attr
from marshmallow import EXCLUDE, Schema, fields, post_load
from pygost import gost341194
from sqlalchemy import DATE, VARCHAR, Column, orm
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base

DATE_FORMAT = "%Y.%m.%d"


Model: DeclarativeMeta = declarative_base()


class Submission(Model):
    __tablename__ = "hundata"

    id = Column("sub_no", VARCHAR(10), nullable=False, primary_key=True)
    date = Column("creation_datetime", DATE(), nullable=False)
    phone_number_hash = Column("tel", VARCHAR(64), nullable=False)
    person_name_hash = Column("phk1", VARCHAR(64), nullable=False)
    person_birthday_hash = Column("dob", VARCHAR(64), nullable=False)


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


def resolve_person_key(submission: Submission) -> str:
    return submission.person_name_hash + submission.person_birthday_hash


class Phone(Protocol):
    number: str


class PhoneServiceConfig(TypedDict):
    delta: int


# TODO: add logs
class PhoneService:

    __slots__ = (
        "delta",
        "hash_factory",
        "person_key_resolver",
    )

    def __init__(self, delta: timedelta):
        self.delta = delta

        self.hash_factory = make_hash
        self.person_key_resolver = resolve_person_key

    def make_hash(self, data: str) -> str:
        return self.hash_factory(data)

    def resolve_person_key(self, submission: Submission) -> str:
        return self.person_key_resolver(submission)

    def verify(self, session: orm.Session, phone: Phone) -> Reliability:
        phone_number = phone.number
        phone_number_hash = self.make_hash(phone_number)

        submissions: List[Submission] = session.query(Submission) \
            .filter(Submission.phone_number_hash == phone_number_hash) \
            .order_by(Submission.date) \
            .all()

        if not submissions:
            return Reliability(status=False, period=None)

        period = Period(submissions[0].date, submissions[-1].date)

        groups: Dict = defaultdict(list)

        for submission in submissions:
            key = self.resolve_person_key(submission)
            groups[key].append(submission)

        for submissions in groups.values():
            if submissions[0].date + self.delta < submissions[-1].date:
                return Reliability(status=True, period=period)

        return Reliability(status=False, period=period)

    @classmethod
    def from_config(cls, config: PhoneServiceConfig) -> "PhoneService":
        return PhoneServiceSchema().load(config)


class PhoneServiceSchema(Schema):
    delta = fields.TimeDelta("days", required=True)

    class Meta:
        unknown = EXCLUDE

    @post_load
    def make_service(self, data: Dict, **kwargs) -> PhoneService:
        return PhoneService(**data)
