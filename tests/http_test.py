"""テストコード。"""

import datetime
import email.utils

import pytest

import pytilpack.http


@pytest.mark.parametrize(
    "retry_after,expected_wait",
    [
        ("5", 5.0),  # 整数秒形式
        ("0", 0.0),  # 0秒
        ("not_a_number", None),  # 無効な値
        ("", None),  # 空文字
    ],
)
def test_get_retry_after_integer(retry_after: str, expected_wait: float | None):
    """_get_retry_after関数の整数秒形式テスト。"""
    result = pytilpack.http.get_retry_after(retry_after)
    assert result == expected_wait


def test_get_retry_after_datetime():
    """_get_retry_after関数の日時形式テスト。"""
    # 現在時刻から5秒後の日時文字列を作成
    future_time = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(seconds=5)
    retry_after = email.utils.formatdate(future_time.timestamp(), usegmt=True)

    result = pytilpack.http.get_retry_after(retry_after)

    # 約5秒（誤差±1秒程度を許容）
    assert result is not None
    assert 4.0 <= result <= 6.0


def test_get_retry_after_past_datetime():
    """_get_retry_after関数の過去の日時形式テスト。"""
    # 現在時刻から5秒前の日時文字列を作成
    past_time = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(seconds=5)
    retry_after = email.utils.formatdate(past_time.timestamp(), usegmt=True)

    result = pytilpack.http.get_retry_after(retry_after)

    # 過去の時刻の場合は0.0を返す
    assert result == 0.0


def test_get_retry_after_invalid_datetime():
    """_get_retry_after関数の無効な日時形式テスト。"""
    result = pytilpack.http.get_retry_after("invalid datetime string")
    assert result is None
