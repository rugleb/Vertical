from typing import Dict

import pytest
from marshmallow import ValidationError

from vertical.app.models import Phone


class TestPhoneModel:

    @pytest.mark.parametrize("number", [
        "74956655173",
        "78006655174",
        "79998887766",
        "79160000000",
    ])
    def test_factory_with_correct_number(self, number: str) -> None:
        data = {
            "number": number,
        }

        phone = Phone.from_dict(data)
        assert isinstance(phone, Phone)

        assert data == phone.to_dict()

    def test_factory_without_data(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            data: Dict = {}
            Phone.from_dict(data)

        exc = exc_info.value
        assert exc.valid_data == {}

        assert exc.messages == {
            "number": [
                "Missing data for required field.",
            ],
        }

    def test_factory_with_nullable_number(self) -> None:
        data = {
            "number": None,
        }

        with pytest.raises(ValidationError) as exc_info:
            Phone.from_dict(data)

        exc = exc_info.value
        assert exc.valid_data == {}

        assert exc.messages == {
            "number": [
                "Field may not be null.",
            ],
        }

    @pytest.mark.parametrize("number", [
        "80000000000",
        "84956655173",
        "799988866554433",
        "799988866",
        "number",
        "",
    ])
    def test_factory_with_incorrect_number(self, number: str) -> None:
        data = {
            "number": number,
        }

        with pytest.raises(ValidationError) as exc_info:
            Phone.from_dict(data)

        exc = exc_info.value
        assert exc.valid_data == {}

        assert exc.messages == {
            "number": [
                "Phone number does't match expected pattern: 7\\d{10}.",
            ],
        }
