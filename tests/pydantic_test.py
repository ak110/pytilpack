import pydantic
import pydantic_core

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


def test_format_error():
    try:
        _TestModel.model_validate({"name": "bob", "age": "twenty"})
    except pydantic.ValidationError as e:
        formatted_error = pytilpack.pydantic.format_error(e)
        assert (
            formatted_error
            == "_TestModel\n"
            + "  age: Input should be a valid integer, unable to parse string as an integer (type=int_parsing, input=twenty)"
        )
    try:
        _TestModel.model_validate({"before_error": True})
    except pydantic.ValidationError as e:
        formatted_error = pytilpack.pydantic.format_error(e)
        assert formatted_error == "_TestModel\n  before_error！ (type=value_error)"
    try:
        _TestModel.model_validate({"name": "after_error", "age": 30})
    except pydantic.ValidationError as e:
        formatted_error = pytilpack.pydantic.format_error(e)
        assert formatted_error == "_TestModel\n  after_error！ (type=かすたむえらー)"


def test_format_exc():
    try:
        _TestModel.model_validate({"age": "twenty"})
    except pydantic.ValidationError:
        formatted_error = pytilpack.pydantic.format_exc()
        assert (
            formatted_error
            == "_TestModel\n"
            + "  name: Field required (type=missing, input={'age': 'twenty'})\n"
            + "  age: Input should be a valid integer, unable to parse string as an integer (type=int_parsing, input=twenty)"
        )
