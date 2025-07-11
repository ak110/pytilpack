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
async def test_run_with_duplicate_names() -> None:
    """重複した名前のチェックでAssertionErrorが発生することをテスト。"""
    checks = [
        pytilpack.healthcheck.make_entry("duplicate", mock_success_check),
        pytilpack.healthcheck.make_entry("duplicate", mock_success_check),
    ]

    with pytest.raises(AssertionError, match="名前の重複"):
        await pytilpack.healthcheck.run(checks)


@pytest.mark.asyncio
async def test_run_response_time() -> None:
    """レスポンス時間が正しく測定されることをテスト。"""
    checks = [
        pytilpack.healthcheck.make_entry("slow", mock_slow_check),
        pytilpack.healthcheck.make_entry("fast", mock_success_check),
    ]

    result = await pytilpack.healthcheck.run(checks)

    details = result.get("details")
    assert details is not None
    slow_time = details["slow"]["response_time_ms"]
    fast_time = details["fast"]["response_time_ms"]

    # 遅いチェックの方が時間がかかっているはず
    assert slow_time > fast_time
    # 遅いチェックは少なくとも100ms程度かかっているはず
    assert slow_time >= 90  # 少し余裕を持って90ms


@pytest.mark.asyncio
async def test_run_error_handling() -> None:
    """エラーハンドリングのテスト。"""
    checks = [
        pytilpack.healthcheck.make_entry("success", mock_success_check),
        pytilpack.healthcheck.make_entry("fail", mock_fail_check),
    ]

    result = await pytilpack.healthcheck.run(checks)

    assert result["status"] == "fail"

    details = result.get("details")
    assert details is not None

    success_detail = details.get("success")
    assert success_detail is not None
    assert success_detail["status"] == "ok"
    assert "error" not in success_detail

    fail_detail = details.get("fail")
    assert fail_detail is not None
    assert fail_detail["status"] == "fail"
    assert fail_detail.get("error") == "ValueError: テストエラー"


@pytest.mark.asyncio
async def test_run_uptime_calculation() -> None:
    """アップタイム計算のテスト。"""
    # StartupTimeを固定値に設定
    original_startup_time = pytilpack.healthcheck.startup_time
    pytilpack.healthcheck.startup_time = datetime.datetime(2024, 1, 1, 10, 0, 0)

    try:
        now = datetime.datetime(2024, 1, 1, 12, 30, 0)
        result = await pytilpack.healthcheck.run([], now=now)

        expected_uptime = now - pytilpack.healthcheck.startup_time
        assert result["uptime"] == str(expected_uptime)

    finally:
        # StartupTimeを元に戻す
        pytilpack.healthcheck.startup_time = original_startup_time
