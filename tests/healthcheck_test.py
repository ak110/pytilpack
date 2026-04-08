"""ヘルスチェック機能のテストコード。"""

import asyncio
import datetime
import time

import pytest

import pytilpack.healthcheck


def sync_success_check() -> None:
    """成功するヘルスチェック。"""
    time.sleep(0.01)  # 短い処理時間をシミュレート


async def mock_success_check() -> None:
    """成功するヘルスチェック。"""
    await asyncio.sleep(0.01)  # 短い処理時間をシミュレート


async def mock_fail_check() -> None:
    """失敗するヘルスチェック。"""
    await asyncio.sleep(0.01)  # 短い処理時間をシミュレート
    raise ValueError("テストエラー")


async def mock_slow_check() -> None:
    """遅いヘルスチェック。"""
    await asyncio.sleep(0.1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "checks,expected_status,expected_details_count,output_details",
    [
        # 成功ケース
        (
            [pytilpack.healthcheck.make_entry("test1", mock_success_check)],
            "ok",
            1,
            True,
        ),
        (
            [
                pytilpack.healthcheck.make_entry("test1", mock_success_check),
                pytilpack.healthcheck.make_entry("test2", mock_success_check),
            ],
            "ok",
            2,
            True,
        ),
        (
            [
                pytilpack.healthcheck.make_entry("test1", sync_success_check),
                pytilpack.healthcheck.make_entry("test2", mock_success_check),
            ],
            "ok",
            2,
            True,
        ),
        # 失敗ケース
        ([pytilpack.healthcheck.make_entry("test1", mock_fail_check)], "fail", 1, True),
        (
            [
                pytilpack.healthcheck.make_entry("test1", mock_success_check),
                pytilpack.healthcheck.make_entry("test2", mock_fail_check),
            ],
            "fail",
            2,
            True,
        ),
        # details非出力ケース
        (
            [pytilpack.healthcheck.make_entry("test1", mock_success_check)],
            "ok",
            1,
            False,
        ),
        # 空リスト
        ([], "ok", 0, True),
    ],
)
async def test_run(
    checks: list[pytilpack.healthcheck.CheckerEntry],
    expected_status: str,
    expected_details_count: int,
    output_details: bool,
) -> None:
    """run関数のテスト。"""
    now = datetime.datetime(2024, 1, 1, 12, 0, 0)

    result = await pytilpack.healthcheck.run(checks=checks, output_details=output_details, now=now)

    # 基本的な構造をチェック
    assert result["status"] == expected_status
    assert result["checked"] == str(now)
    assert "uptime" in result

    # details の確認
    if output_details:
        assert "details" in result
        assert len(result["details"]) == expected_details_count

        # 各詳細をチェック
        for name, detail in result.get("details", {}).items():
            assert name in [check[0] for check in checks]
            assert detail["status"] in ["ok", "fail"]
            assert isinstance(detail["response_time_ms"], int | float)
            assert detail["response_time_ms"] >= 0
            if detail["status"] == "ok":
                assert "error" not in detail
            else:
                assert detail.get("error") is not None
    else:
        assert "details" not in result


@pytest.mark.asyncio
async def test_run_misc() -> None:
    """run関数の重複名・レスポンス時間・エラーハンドリング・アップタイムのテスト。"""
    # 重複した名前のチェックでAssertionErrorが発生
    checks_dup = [
        pytilpack.healthcheck.make_entry("duplicate", mock_success_check),
        pytilpack.healthcheck.make_entry("duplicate", mock_success_check),
    ]
    with pytest.raises(AssertionError, match="ヘルスチェック名が重複しています"):
        await pytilpack.healthcheck.run(checks_dup)

    # レスポンス時間の測定
    checks_time = [
        pytilpack.healthcheck.make_entry("slow", mock_slow_check),
        pytilpack.healthcheck.make_entry("fast", mock_success_check),
    ]
    result = await pytilpack.healthcheck.run(checks_time)
    details = result.get("details")
    assert details is not None
    assert details["slow"]["response_time_ms"] > details["fast"]["response_time_ms"]
    assert details["slow"]["response_time_ms"] >= 90  # 少し余裕を持って90ms

    # エラーハンドリング
    checks_err = [
        pytilpack.healthcheck.make_entry("success", mock_success_check),
        pytilpack.healthcheck.make_entry("fail", mock_fail_check),
    ]
    result = await pytilpack.healthcheck.run(checks_err)
    assert result["status"] == "fail"
    details = result.get("details")
    assert details is not None
    assert details["success"]["status"] == "ok"
    assert "error" not in details["success"]
    assert details["fail"]["status"] == "fail"
    assert details["fail"].get("error") == "ValueError: テストエラー"

    # アップタイム計算: start_timeパラメータ経由で起動時刻を注入
    start = datetime.datetime(2024, 1, 1, 10, 0, 0)
    now = datetime.datetime(2024, 1, 1, 12, 30, 0)
    result = await pytilpack.healthcheck.run([], now=now, start_time=start)
    assert result["uptime"] == str(now - start)
