"""CSV関連のユーティリティ集。"""

import csv
import pathlib
import typing


def read_to_dict(
    path: str | pathlib.Path,
    fieldnames: list[str],
    skipinitialspace: bool = True,
    lineterminator: str = "\n",
) -> list[dict[str, typing.Any]]:
    """CSVファイルを辞書型のリストとして読み込む。

    Args:
        path: CSVファイルのパス。
        fieldnames: CSVファイルのフィールド名。
        skipinitialspace: 先頭の空白をスキップするか。
        lineterminator: 行の終端文字。

    Returns:
        CSVファイルの内容。

    """
    path = pathlib.Path(path)
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(
            f,
            fieldnames=fieldnames,
            skipinitialspace=skipinitialspace,
            lineterminator=lineterminator,
        )
        reader = csv.DictReader(f)
        return list(reader)
