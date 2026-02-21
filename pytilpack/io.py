"""IO関連のユーティリティ。"""

import io
import pathlib
import typing

PathOrIO = str | pathlib.Path | typing.IO[str] | typing.IO[bytes]
"""パスまたはIOオブジェクトな型。"""


def read_text(
    source: PathOrIO,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> str:
    """パスまたはIOオブジェクトからテキストを読み込む。

    パスの場合はファイルが存在しない場合FileNotFoundErrorを発生させる。

    """
    if isinstance(source, (str, pathlib.Path)):
        return pathlib.Path(source).read_text(encoding=encoding, errors=errors)
    content = source.read()
    if isinstance(content, str):
        return content
    return bytes(content).decode(encoding=encoding, errors=errors)


def write_text(
    dest: PathOrIO,
    text: str,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> None:
    """パスまたはIOオブジェクトにテキストを書き込む。

    パスの場合は親ディレクトリを自動作成する。

    """
    if isinstance(dest, (str, pathlib.Path)):
        p = pathlib.Path(dest)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding=encoding, errors=errors)
    elif isinstance(dest, (io.RawIOBase, io.BufferedIOBase)):
        typing.cast(typing.IO[bytes], dest).write(text.encode(encoding=encoding, errors=errors))
    else:
        typing.cast(typing.IO[str], dest).write(text)
