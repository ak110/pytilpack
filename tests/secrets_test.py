import concurrent.futures
import multiprocessing
import os
import pathlib
import sys
import typing

import pytest

import pytilpack.secrets

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="pytilpack.secretsはUnix専用のfcntlに依存するため")


def test_generate_secret_key(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "secret_key"
    assert not path.exists()
    secret_key1 = pytilpack.secrets.generate_secret_key(path, nbytes=17)
    assert path.exists()
    secret_key2 = pytilpack.secrets.generate_secret_key(path)
    assert len(secret_key1) == 17
    assert secret_key1 == secret_key2 == path.read_bytes()
    assert (os.stat(path).st_mode & 0o777) == 0o600


def test_generate_secret_key_permission_with_open_umask(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "secret_key"
    original_open = os.open
    modes: list[int] = []

    def record_open(file: typing.Any, flags: int, mode: int = 0o777, **kwargs: typing.Any) -> int:
        if pathlib.Path(file) == path and flags & os.O_CREAT:
            modes.append(mode)
        return original_open(file, flags, mode, **kwargs)

    monkeypatch.setattr(pytilpack.secrets.os, "open", record_open)
    old_umask = os.umask(0o000)
    try:
        pytilpack.secrets.generate_secret_key(path)
        assert modes == [0o600]
        assert (os.stat(path).st_mode & 0o777) == 0o600
    finally:
        os.umask(old_umask)


def test_generate_secret_key_concurrent(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "secret_key"
    for _ in range(2):
        path.unlink(missing_ok=True)

        with concurrent.futures.ProcessPoolExecutor(
            max_workers=2, mp_context=multiprocessing.get_context("spawn")
        ) as process_executor:
            process_futures = [process_executor.submit(_run_threads, path, 2) for _ in range(2)]
            results = sum(
                (future.result() for future in concurrent.futures.as_completed(process_futures)),
                [],
            )

        assert len(results) == 4
        saved_key = path.read_bytes()
        assert len(saved_key) == 17
        assert results == [saved_key] * 4


def _run_threads(path: pathlib.Path, thread_count: int) -> list[bytes]:

    def call_generate_secret_key() -> bytes:
        return pytilpack.secrets.generate_secret_key(path, nbytes=17)

    with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as thread_executor:
        thread_futures = [thread_executor.submit(call_generate_secret_key) for _ in range(thread_count)]
        return [future.result() for future in concurrent.futures.as_completed(thread_futures)]
