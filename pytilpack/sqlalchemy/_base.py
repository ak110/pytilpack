"""SQLAlchemy Mixin共通の基底クラス。"""

import typing

_SENTINEL = object()


class _ReprMixin:
    """__repr__を提供する共通Mixin。"""

    def _repr_attrs(self) -> dict[str, typing.Any]:
        """__repr__で表示する属性を返す。派生クラスでオーバーライド可能。"""
        id_ = getattr(self, "id", _SENTINEL)
        if id_ is not _SENTINEL:
            return {"id": id_}
        return {}

    def __repr__(self) -> str:
        # detached/expired状態でのDetachedInstanceErrorなどを防ぐ
        try:
            attrs = self._repr_attrs()
            attrs_str = ", ".join(f"{k}={v!r}" for k, v in attrs.items())
            return f"<{self.__class__.__module__}.{self.__class__.__qualname__}({attrs_str})>"
        except Exception:
            return f"<{self.__class__.__module__}.{self.__class__.__qualname__}>"
