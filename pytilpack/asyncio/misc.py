"""asyncio用のユーティリティ集。"""

import asyncio


def get_task_id() -> int | None:
    """現在のタスクIDを取得する。

    Returns:
        タスクID。タスクが存在しない場合はNone。

    """
    task = asyncio.current_task()
    return id(task) if task is not None else None
