"""テストコード。"""

import pydantic
import pydantic_core

import pytilpack.pydantic


class TestModel(pydantic.BaseModel):
    """テスト用のPydanticモデル。"""

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
    """Pydanticのバリデーションエラーの整形テスト。"""
    try:
        TestModel.model_validate({"name": "bob", "age": "twenty"})
    except pydantic.ValidationError as e:
        formatted_error = pytilpack.pydantic.format_error(e)
        assert (
            formatted_error
            == "TestModel\n"
            + "  age: Input should be a valid integer, unable to parse string as an integer (type=int_parsing, input=twenty)"
        )
    # _validate_before
    try:
        TestModel.model_validate({"before_error": True})
    except pydantic.ValidationError as e:
        formatted_error = pytilpack.pydantic.format_error(e)
        assert formatted_error == "TestModel\n  before_error！ (type=value_error)"
    # _validate_after
    try:
        TestModel.model_validate({"name": "after_error", "age": 30})
    except pydantic.ValidationError as e:
        formatted_error = pytilpack.pydantic.format_error(e)
        assert formatted_error == "TestModel\n  after_error！ (type=かすたむえらー)"


def test_format_exc():
    """Pydanticのバリデーションエラーの整形テスト。"""
    try:
        TestModel.model_validate({"age": "twenty"})
    except pydantic.ValidationError:
        formatted_error = pytilpack.pydantic.format_exc()
        assert (
            formatted_error
            == "TestModel\n"
            + "  name: Field required (type=missing, input={'age': 'twenty'})\n"
            + "  age: Input should be a valid integer, unable to parse string as an integer (type=int_parsing, input=twenty)"
        )
