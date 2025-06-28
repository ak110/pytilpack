"""テストコード。"""

import concurrent.futures
import multiprocessing
import os
import pathlib

import pytilpack.secrets


def test_generate_secret_key(tmp_path: pathlib.Path) -> None:
    """generate_secret_keyの基本テスト。"""
    path = tmp_path / "secret_key"
    assert not path.exists()
    secret_key1 = pytilpack.secrets.generate_secret_key(path)
    assert path.exists()
    secret_key2 = pytilpack.secrets.generate_secret_key(path)
    assert secret_key1 == secret_key2
    # パーミッションの確認
    assert (os.stat(path).st_mode & 0o777) == 0o600


def test_generate_secret_key_concurrent(tmp_path: pathlib.Path) -> None:
    """4プロセス×4スレッドで同時実行して同じ値が返ることを確認。"""
    path = tmp_path / "secret_key"
    # 4回試す
    for _ in range(4):
        path.unlink(missing_ok=True)  # 前のファイルを削除

        # 4プロセスで並列実行
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=4, mp_context=multiprocessing.get_context("spawn")
        ) as process_executor:
            process_futures = [process_executor.submit(_run_threads, path, 4) for _ in range(4)]
            results = sum(
                (future.result() for future in concurrent.futures.as_completed(process_futures)),
                [],
            )

        # 全ての結果が同じ値であることを確認
        assert len(results) == 16
        assert all(result == results[0] for result in results)


def _run_threads(path: pathlib.Path, thread_count: int) -> list[bytes]:
    """指定された数のスレッドでgenerate_secret_keyを実行。"""

    def call_generate_secret_key() -> bytes:
        return pytilpack.secrets.generate_secret_key(path)

    with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as thread_executor:
        thread_futures = [thread_executor.submit(call_generate_secret_key) for _ in range(thread_count)]
        return [future.result() for future in concurrent.futures.as_completed(thread_futures)]
