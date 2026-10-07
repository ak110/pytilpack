"""同期I/Oのテスト。"""

import io
import pathlib

import pytest

import pytilpack.io


@pytest.mark.parametrize("use_string_path", [False, True])
def test_read_write_text_path(tmp_path: pathlib.Path, use_string_path: bool) -> None:
    """親ディレクトリを作成し、パスから書き込んだテキストを読み戻す。"""
    path = tmp_path / "nested" / "sample.txt"
    target = str(path) if use_string_path else path
    pytilpack.io.write_text(target, "日本語\nテキスト")
    assert path.read_bytes() == "日本語\nテキスト".encode()
    assert pytilpack.io.read_text(target) == "日本語\nテキスト"


@pytest.mark.parametrize("binary", [False, True])
def test_read_write_text_stream(binary: bool) -> None:
    """テキスト・バイナリのストリームへ書き込み、読み戻す。"""
    stream = io.BytesIO() if binary else io.StringIO()
    pytilpack.io.write_text(stream, "日本語", encoding="shift_jis")
    assert stream.getvalue() == ("日本語".encode("shift_jis") if binary else "日本語")
    stream.seek(0)
    assert pytilpack.io.read_text(stream, encoding="shift_jis") == "日本語"


def test_read_text_missing_path(tmp_path: pathlib.Path) -> None:
    """存在しないパスはFileNotFoundErrorを返す。"""
    with pytest.raises(FileNotFoundError):
        pytilpack.io.read_text(tmp_path / "missing.txt")


def test_text_encoding_errors(tmp_path: pathlib.Path) -> None:
    """パスとバイナリストリームに指定した文字コードとエラー処理を適用する。"""
    path = tmp_path / "sample.txt"
    pytilpack.io.write_text(path, "日本語", encoding="shift_jis")
    assert path.read_bytes() == "日本語".encode("shift_jis")
    assert pytilpack.io.read_text(path, encoding="shift_jis") == "日本語"
    path.write_bytes(b"\xff")
    assert pytilpack.io.read_text(path) == "\ufffd"
    with pytest.raises(UnicodeDecodeError):
        pytilpack.io.read_text(path, errors="strict")
    assert pytilpack.io.read_text(io.BytesIO(b"\xff")) == "\ufffd"
    with pytest.raises(UnicodeDecodeError):
        pytilpack.io.read_text(io.BytesIO(b"\xff"), errors="strict")
    pytilpack.io.write_text(path, "a日本語b", encoding="ascii", errors="ignore")
    assert path.read_bytes() == b"ab"
    stream = io.BytesIO()
    pytilpack.io.write_text(stream, "a日本語b", encoding="ascii", errors="ignore")
    assert stream.getvalue() == b"ab"
