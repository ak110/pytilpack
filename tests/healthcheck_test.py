import contextvars
import datetime as dt
import types

import pytest

import pytilpack.healthcheck


def sync_success_check() -> None:
    pass


async def mock_success_check() -> None:
    pass


async def mock_fail_check() -> None:
    raise ValueError("テストエラー")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "checkers,expected_status,expected_errors,output_details",
    [
        ([mock_success_check], "ok", [None], True),
        ([mock_success_check, mock_success_check], "ok", [None, None], True),
        ([sync_success_check, mock_success_check], "ok", [None, None], True),
        ([mock_fail_check], "fail", ["ValueError: テストエラー"], True),
        ([mock_success_check, mock_fail_check], "fail", [None, "ValueError: テストエラー"], True),
        ([mock_success_check], "ok", [None], False),
        ([], "ok", [], True),
    ],
)
async def test_run(checkers, expected_status: str, expected_errors: list[str | None], output_details: bool) -> None:
    checks = [pytilpack.healthcheck.make_entry(f"check-{i}", check) for i, check in enumerate(checkers)]
    start = dt.datetime(2024, 1, 1, 10)
    now = dt.datetime(2024, 1, 1, 12, 30)
    result = await pytilpack.healthcheck.run(checks, output_details=output_details, now=now, start_time=start)

    assert result["status"] == expected_status
    assert result["checked"] == str(now)
    assert result["uptime"] == str(now - start)

    if output_details:
        details = result.get("details")
        assert details is not None
        assert details.keys() == {name for name, _ in checks}
        for (name, _), error in zip(checks, expected_errors, strict=True):
            detail = details[name]
            assert detail["response_time_ms"] >= 0
            if error is None:
                assert detail["status"] == "ok"
                assert "error" not in detail
            else:
                assert detail["status"] == "fail"
                assert detail.get("error") == error
    else:
        assert "details" not in result


@pytest.mark.asyncio
async def test_run_duplicate_names() -> None:
    checks = [pytilpack.healthcheck.make_entry("duplicate", mock_success_check)] * 2
    with pytest.raises(AssertionError, match="ヘルスチェック名が重複しています"):
        await pytilpack.healthcheck.run(checks)


@pytest.mark.asyncio
async def test_run_response_time(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = contextvars.ContextVar("clock", default=10.0)

    async def advance_clock(seconds: float) -> None:
        clock.set(clock.get() + seconds)

    monkeypatch.setattr(pytilpack.healthcheck, "time", types.SimpleNamespace(perf_counter=clock.get))
    checks = [
        pytilpack.healthcheck.make_entry("slow", advance_clock, 0.125),
        pytilpack.healthcheck.make_entry("fast", advance_clock, 0.015625),
    ]
    result = await pytilpack.healthcheck.run(checks)
    details = result.get("details")
    assert details is not None
    assert details["slow"]["response_time_ms"] == 125
    assert details["fast"]["response_time_ms"] == 15
