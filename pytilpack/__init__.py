"""ppytilpack: Pythonの各種ライブラリのユーティリティ集。"""

import importlib
import types


def __getattr__(name: str) -> types.ModuleType:
    """旧バージョンの互換性のための処理。"""
    if name.endswith("_"):
        import sys
        import warnings

        old_name = name.rstrip("_")
        module = importlib.import_module(f"{__name__}.{old_name}")
        sys.modules[f"{__name__}.{name}"] = module
        warnings.warn(
            f"Module '{__name__}.{name}' is deprecated, use '{__name__}.{old_name}' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return module
    else:
        return importlib.import_module(f"{__name__}.{name}")
