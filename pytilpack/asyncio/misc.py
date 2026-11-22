__lazy_modules__ = ["asyncio"]

import asyncio

__all__ = ["get_task_id", "get_task_id_hex"]


def get_task_id() -> int | None:
    task = asyncio.current_task()
    return id(task) if task is not None else None


def get_task_id_hex() -> str:
    task_id = get_task_id()
    return f"{task_id:x}" if task_id is not None else "None"
