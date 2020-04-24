import re
from typing import Dict, Final

import attr
from marshmallow import Schema, ValidationError, fields, post_load

__all__ = (
    "Phone",
    "PhoneSchema",
)

PHONE_NUMBER_FORMAT: Final = re.compile(r"7\d{10}")


def validate_phone_number(number: str) -> None:
    if not PHONE_NUMBER_FORMAT.fullmatch(number):
        pattern = PHONE_NUMBER_FORMAT.pattern
        message = f"Phone number does't match expected pattern: {pattern}."
        raise ValidationError(message)


@attr.s(slots=True, frozen=True)
class Phone:
    number: str = attr.ib()

    def to_dict(self) -> Dict:
        return PHONE_SCHEMA.dump(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Phone":
        return PHONE_SCHEMA.load(data)


class PhoneSchema(Schema):
    number = fields.Str(required=True, validate=validate_phone_number)

    @post_load
    def make_model(self, data: Dict, **kwargs) -> Phone:
        return Phone(**data)


PHONE_SCHEMA: Final = PhoneSchema()
