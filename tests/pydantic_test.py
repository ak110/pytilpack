import re

import pydantic
import pydantic_core
import pytest

import pytilpack.pydantic


class _TestModel(pydantic.BaseModel):
    name: str
    age: int

    @pydantic.model_validator(mode="before")
    @classmethod
    def _validate_before(cls, data):
        if "before_error" in data:
            raise ValueError("before_error！")
        return data

    @pydantic.model_validator(mode="after")
    def _validate_after(self):
        if self.name == "after_error":
            raise pydantic_core.PydanticCustomError("かすたむえらー", "after_error！")
        return self


@pytest.mark.parametrize(
    ("data", "diagnostic"),
    [
        ({"name": "bob", "age": "twenty"}, r"  age: .+ \(type=int_parsing, input=twenty\)"),
        ({"before_error": True}, r"  before_error！ \(type=value_error\)"),
        ({"name": "after_error", "age": 30}, r"  after_error！ \(type=かすたむえらー\)"),
    ],
)
def test_format_error(data, diagnostic):
    with pytest.raises(pydantic.ValidationError) as caught:
        _TestModel.model_validate(data)
    title, line = pytilpack.pydantic.format_error(caught.value).splitlines()
    assert title == "_TestModel"
    assert re.fullmatch(diagnostic, line)


def test_format_exc():
    try:
        _TestModel.model_validate({"age": "twenty"})
    except pydantic.ValidationError:
        title, name, age = pytilpack.pydantic.format_exc().splitlines()
        assert title == "_TestModel"
        assert name.startswith("  name: ")
        assert name.endswith("(type=missing, input={'age': 'twenty'})")
        assert age.startswith("  age: ")
        assert age.endswith("(type=int_parsing, input=twenty)")
    else:
        pytest.fail("Expected validation to fail")
