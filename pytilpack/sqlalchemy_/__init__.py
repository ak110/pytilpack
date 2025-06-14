"""SQLAlchemy用のユーティリティ集。"""

# 非同期版
from .async_ import AsyncMixin, AsyncUniqueIDMixin, asafe_close, await_for_connection

# ユーティリティ
from .describe import describe, describe_table, get_class_by_table

# Flask-SQLAlchemy版
from .flask_ import Mixin, UniqueIDMixin, register_ping

# 同期版
from .sync_ import SyncMixin, SyncUniqueIDMixin, safe_close, wait_for_connection

__all__ = [
    # Flask-SQLAlchemy版
    "Mixin",
    "UniqueIDMixin",
    "register_ping",
    "safe_close",
    "wait_for_connection",
    # 非同期版
    "AsyncMixin",
    "AsyncUniqueIDMixin",
    "asafe_close",
    "await_for_connection",
    # 同期版
    "SyncMixin",
    "SyncUniqueIDMixin",
    # ユーティリティ
    "describe",
    "describe_table",
    "get_class_by_table",
]
