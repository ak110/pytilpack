"""テストコード。"""

import pathlib

import pytest

import pytilpack.pytest


def test_assert_block_no_error(tmp_path: pathlib.Path) -> None:
    with pytilpack.pytest.AssertBlock("data", suffix=".txt", tmp_path=tmp_path):
        pass


def test_assert_block_assertion_error(tmp_path: pathlib.Path) -> None:
    with pytest.raises(AssertionError) as exc_info, pytilpack.pytest.AssertBlock("test data", suffix=".txt", tmp_path=tmp_path):
        raise AssertionError("test error")
    assert "test error" in str(exc_info.value)
    assert ".txt" in str(exc_info.value)


def test_assert_block_bytes(tmp_path: pathlib.Path) -> None:
    with (
        pytest.raises(AssertionError) as exc_info,
        pytilpack.pytest.AssertBlock(b"\x00\x01\x02", suffix=".bin", tmp_path=tmp_path),
    ):
        raise AssertionError("binary error")
    assert "binary error" in str(exc_info.value)
    assert ".bin" in str(exc_info.value)


@pytest.mark.asyncio
async def test_assert_block_async(tmp_path: pathlib.Path) -> None:
    async with pytilpack.pytest.AssertBlock("async data", suffix=".txt", tmp_path=tmp_path):
        pass

    with pytest.raises(AssertionError) as exc_info:
        async with pytilpack.pytest.AssertBlock("async data", suffix=".txt", tmp_path=tmp_path):
            raise AssertionError("async error")
    assert "async error" in str(exc_info.value)
    assert ".txt" in str(exc_info.value)


def test_tmp_file_path() -> None:
    assert pytilpack.pytest.tmp_file_path().exists()


def test_tmp_path(tmp_path: pathlib.Path) -> None:
    assert pytilpack.pytest.get_tmp_path() == tmp_path.parent
