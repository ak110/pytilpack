"""import関連。"""

import importlib
import logging
import pathlib

logger = logging.getLogger(__name__)


def import_all(path: pathlib.Path, base_path: pathlib.Path | None = None, ignore_test: bool = True) -> None:
    """指定されたパス配下のすべての*.pyファイルをインポートする。

    Args:
        path: インポート対象のパス。
        base_path: 相対パスの基準となるパス。Noneの場合はpathを使用。
        ignore_test: テストファイルを無視するかどうか。デフォルトはTrue。

    """
    if base_path is None:
        base_path = path

    for item in sorted(path.rglob("*.py")):
        if ignore_test and item.name.startswith("test_") or item.name.endswith("_test.py"):
            continue
        import_path = item.parent if item.name == "__init__.py" else item.with_suffix("")
        module_name = ".".join(import_path.relative_to(base_path).parts)
        logger.debug(f"Importing module: {module_name}")
        importlib.import_module(module_name)
