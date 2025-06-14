"""SQLAlchemy用のユーティリティ集。"""

# async版
from .async_ import AsyncMixin, AsyncUniqueIDMixin, asafe_close, await_for_connection
from .describe import describe, describe_table, get_class_by_table

# Flask-SQLAlchemy版
from .flask_ import Mixin, UniqueIDMixin, register_ping

# 同期版
from .sync_ import SyncMixin, SyncUniqueIDMixin, safe_close, wait_for_connection

__all__ = [
    # Flask-SQLAlchemy版
    "Mixin",
    "UniqueIDMixin",
    "describe",
    "describe_table",
    "get_class_by_table",
    "register_ping",
    "safe_close",
    "wait_for_connection",
    # async版
    "AsyncMixin",
    "AsyncUniqueIDMixin",
    "asafe_close",
    "await_for_connection",
    # 同期版
    "SyncMixin",
    "SyncUniqueIDMixin",
]
