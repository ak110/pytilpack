"""CSV関連のユーティリティ集。"""

__lazy_modules__ = ["csv", "pathlib", "typing"]

import csv
import pathlib
import typing


def read_to_dict(
    path: str | pathlib.Path,
    fieldnames: list[str],
    skipinitialspace: bool = True,
    lineterminator: str = "\n",
    encoding: str = "utf-8",
) -> list[dict[str, typing.Any]]:
    """CSVファイルを辞書型のリストとして読み込む。

    Args:
        path: CSVファイルのパス。
        fieldnames: CSVファイルのフィールド名。
        skipinitialspace: 先頭の空白をスキップするか。
        lineterminator: 互換性のため受け取る引数。読み込みでは使われず、改行はCRまたはLFで認識する。
        encoding: ファイルの文字エンコーディング。

    Returns:
        CSVファイルの内容。

    """
    path = pathlib.Path(path)
    with path.open(encoding=encoding) as f:
        reader = csv.DictReader(
            f,
            fieldnames=fieldnames,
            skipinitialspace=skipinitialspace,
            lineterminator=lineterminator,
        )
        return list(reader)
