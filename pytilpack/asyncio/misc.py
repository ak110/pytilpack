"""asyncio用のユーティリティ集。"""

import asyncio


def get_task_id() -> int | None:
    """現在のタスクIDを取得する。

    Returns:
        タスクID。タスクが存在しない場合はNone。

    """
    task = asyncio.current_task()
    return id(task) if task is not None else None


def get_task_id_hex() -> str:
    """現在のタスクIDを16進数文字列で取得する。

    Returns:
        タスクIDの16進数文字列。タスクが存在しない場合は"None"。

    """
    task_id = get_task_id()
    return f"{task_id:x}" if task_id is not None else "None"
