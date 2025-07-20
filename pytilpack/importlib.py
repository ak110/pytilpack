"""import関連。"""

import importlib
import logging
import pathlib

logger = logging.getLogger(__name__)


def import_all(path: pathlib.Path, base_path: pathlib.Path | None = None) -> None:
    """指定されたパス配下のすべての*.pyファイルをインポートする。"""
    if base_path is None:
        base_path = path

    for item in sorted(path.rglob("*.py")):
        import_path = item.parent if item.name == "__init__.py" else item.with_suffix("")
        module_name = ".".join(import_path.relative_to(base_path).parts)
        logger.debug(f"Importing module: {module_name}")
        importlib.import_module(module_name)
