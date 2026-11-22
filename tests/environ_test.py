import decimal
import pathlib

import pytest

import pytilpack.environ


def test_get_str() -> None:
    env = {"TEST_STR": "hello"}
    assert pytilpack.environ.get_str("TEST_STR", environ=env) == "hello"
    assert pytilpack.environ.get_str("TEST_STR", "default", environ=env) == "hello"
    assert pytilpack.environ.get_str("TEST_STR", "default", environ={}) == "default"
    with pytest.raises(ValueError, match="TEST_STR"):
        pytilpack.environ.get_str("TEST_STR", environ={})


def test_get_int() -> None:
    env = {"TEST_INT": "42"}
    assert pytilpack.environ.get_int("TEST_INT", environ=env) == 42
    assert pytilpack.environ.get_int("TEST_INT", 0, environ=env) == 42
    assert pytilpack.environ.get_int("TEST_INT", 99, environ={}) == 99
    with pytest.raises(ValueError, match="TEST_INT"):
        pytilpack.environ.get_int("TEST_INT", environ={})
    with pytest.raises(ValueError):
        pytilpack.environ.get_int("TEST_INT", environ={"TEST_INT": "abc"})


def test_get_float() -> None:
    env = {"TEST_FLOAT": "3.14"}
    assert pytilpack.environ.get_float("TEST_FLOAT", environ=env) == pytest.approx(3.14)
    assert pytilpack.environ.get_float("TEST_FLOAT", 1.0, environ={}) == 1.0


def test_get_bool() -> None:
    for true_val in ("true", "True", "TRUE", "1"):
        assert pytilpack.environ.get_bool("K", environ={"K": true_val}) is True
    for false_val in ("false", "False", "FALSE", "0"):
        assert pytilpack.environ.get_bool("K", environ={"K": false_val}) is False
    assert pytilpack.environ.get_bool("K", True, environ={}) is True
    with pytest.raises(ValueError):
        pytilpack.environ.get_bool("K", environ={"K": "invalid"})


def test_get_decimal() -> None:
    env = {"TEST_DECIMAL": "3.14159"}
    assert pytilpack.environ.get_decimal("TEST_DECIMAL", environ=env) == decimal.Decimal("3.14159")
    assert pytilpack.environ.get_decimal("TEST_DECIMAL", decimal.Decimal("0"), environ={}) == decimal.Decimal("0")
    with pytest.raises(ValueError):
        pytilpack.environ.get_decimal("TEST_DECIMAL", environ={"TEST_DECIMAL": "not-a-number"})


def test_get_path() -> None:
    env = {"TEST_PATH": "/tmp/test"}
    result = pytilpack.environ.get_path("TEST_PATH", environ=env)
    assert isinstance(result, pathlib.Path)
    assert result == pathlib.Path("/tmp/test").resolve()
    default = pathlib.Path("/default")
    assert pytilpack.environ.get_path("TEST_PATH", default, environ={}) == default


def test_get_list() -> None:
    env = {"TEST_LIST": "a,b,c"}
    assert pytilpack.environ.get_list("TEST_LIST", environ=env) == ["a", "b", "c"]
    env = {"TEST_LIST": " a , b , c "}
    assert pytilpack.environ.get_list("TEST_LIST", environ=env) == ["a", "b", "c"]
    env = {"TEST_LIST": "a,,b,,c"}
    assert pytilpack.environ.get_list("TEST_LIST", environ=env) == ["a", "b", "c"]
    env = {"TEST_LIST": "a:b:c"}
    assert pytilpack.environ.get_list("TEST_LIST", separator=":", environ=env) == [
        "a",
        "b",
        "c",
    ]
    assert pytilpack.environ.get_list("TEST_LIST", default=["x"], environ={}) == ["x"]
    with pytest.raises(ValueError, match="TEST_LIST"):
        pytilpack.environ.get_list("TEST_LIST", environ={})


def test_get_or_none() -> None:
    assert pytilpack.environ.get_or_none("TEST_KEY", environ={"TEST_KEY": "value"}) == "value"
    assert pytilpack.environ.get_or_none("TEST_KEY", environ={}) is None


def test_load_dotenv(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DOTENV_TEST_VAR=dotenv_value\n")
    monkeypatch.delenv("DOTENV_TEST_VAR", raising=False)
    assert pytilpack.environ.get_or_none("DOTENV_TEST_VAR") is None
    pytilpack.environ.load_dotenv(env_file)
    assert pytilpack.environ.get_or_none("DOTENV_TEST_VAR") == "dotenv_value"
    monkeypatch.delenv("DOTENV_TEST_VAR", raising=False)


def test_missing_messages() -> None:
    with pytest.raises(ValueError, match="環境変数 X が設定されていません。環境変数を設定するか、default引数を指定する"):
        pytilpack.environ.get_str("X", environ={})
    with pytest.raises(ValueError, match="環境変数 X が設定されていません。環境変数を設定するか、default引数を指定する"):
        pytilpack.environ.get_list("X", environ={})
