import pathlib

import pytest

import pytilpack.pytest


def test_assert_block_no_error(tmp_path: pathlib.Path) -> None:
    with pytilpack.pytest.AssertBlock("data", suffix=".txt", tmp_path=tmp_path):
        pass
    assert not list(tmp_path.iterdir())


def _assert_saved_diagnostic(
    tmp_path: pathlib.Path, error: AssertionError, cause: AssertionError, suffix: str, contents: bytes
) -> None:
    (saved,) = tmp_path.iterdir()
    assert saved.suffix == suffix
    assert saved.read_bytes() == contents
    assert f"<{saved}>" in str(error)
    assert str(cause) in str(error)
    assert error.__cause__ is cause


def test_assert_block_assertion_error(tmp_path: pathlib.Path) -> None:
    cause = AssertionError("test error")
    with pytest.raises(AssertionError) as exc_info, pytilpack.pytest.AssertBlock("診断", suffix=".txt", tmp_path=tmp_path):
        raise cause
    _assert_saved_diagnostic(tmp_path, exc_info.value, cause, ".txt", "診断".encode())


def test_assert_block_bytes(tmp_path: pathlib.Path) -> None:
    data = bytes((0, 1, 255))
    cause = AssertionError("binary error")
    with pytest.raises(AssertionError) as exc_info, pytilpack.pytest.AssertBlock(data, suffix=".bin", tmp_path=tmp_path):
        raise cause
    _assert_saved_diagnostic(tmp_path, exc_info.value, cause, ".bin", data)


@pytest.mark.asyncio
async def test_assert_block_async(tmp_path: pathlib.Path) -> None:
    async with pytilpack.pytest.AssertBlock("async data", suffix=".txt", tmp_path=tmp_path):
        pass
    assert not list(tmp_path.iterdir())

    cause = AssertionError("async error")
    with pytest.raises(AssertionError) as exc_info:
        async with pytilpack.pytest.AssertBlock("async data", suffix=".txt", tmp_path=tmp_path):
            raise cause
    _assert_saved_diagnostic(tmp_path, exc_info.value, cause, ".txt", b"async data")


def test_tmp_file_path(tmp_path: pathlib.Path) -> None:
    existing = tmp_path / "capture-existing.log"
    existing.touch()
    explicit = pytilpack.pytest.tmp_file_path(tmp_path, prefix="capture-", suffix=".log")
    assert explicit.is_file()
    assert set(tmp_path.iterdir()) == {existing, explicit}
    assert explicit.name.startswith("capture-")
    assert explicit.suffix == ".log"

    registered = pytilpack.pytest.get_tmp_path()
    before = set(registered.glob("g3-capture-*.log"))
    default = pytilpack.pytest.tmp_file_path(prefix="g3-capture-", suffix=".log")
    assert default.is_file()
    assert default.parent == registered
    assert default not in before


def test_tmp_path(tmp_path: pathlib.Path) -> None:
    assert pytilpack.pytest.get_tmp_path() == tmp_path.parent
