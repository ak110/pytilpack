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
    path = pathlib.Path(path)
    with path.open(encoding=encoding) as f:
        reader = csv.DictReader(
            f,
            fieldnames=fieldnames,
            skipinitialspace=skipinitialspace,
            lineterminator=lineterminator,
        )
        return list(reader)
