"""テストコード。"""

import pydantic

import pytilpack.pydantic


class TestModel(pydantic.BaseModel):
    """テスト用のPydanticモデル。"""

    name: str
    age: int


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
