"""babelのテスト。"""

import datetime
import pathlib

import pytilpack.babel
import pytilpack.i18n

LOCALES_DIR = pathlib.Path(__file__).parent / "fixtures" / "locales"


def test_format_date() -> None:
    """日付フォーマットのテスト。"""
    state = pytilpack.i18n.I18nState(LOCALES_DIR, default_locale="ja")
    tokens = pytilpack.i18n.activate(state, "ja")
    try:
        date = datetime.date(2024, 1, 15)
        result = pytilpack.babel.format_date(date, format="long")
        assert "2024" in result
        assert "1" in result
        assert "15" in result
    finally:
        pytilpack.i18n.deactivate(tokens)


def test_format_datetime() -> None:
    """日時フォーマットのテスト。"""
    dt = datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)
    # ロケール指定で直接呼び出し
    result = pytilpack.babel.format_datetime(dt, format="short", locale="en")
    assert "1/15/24" in result


def test_format_time() -> None:
    """時刻フォーマットのテスト。"""
    t = datetime.time(14, 30, 0)
    result = pytilpack.babel.format_time(t, format="short", locale="ja")
    assert "14:30" in result


def test_format_number() -> None:
    """数値フォーマットのテスト。"""
    assert pytilpack.babel.format_number(1234567, locale="en") == "1,234,567"
    result_ja = pytilpack.babel.format_number(1234567, locale="ja")
    assert "1,234,567" in result_ja


def test_format_currency() -> None:
    """通貨フォーマットのテスト。"""
    result = pytilpack.babel.format_currency(1234, "JPY", locale="ja")
    assert "1,234" in result
    assert "￥" in result or "¥" in result


def test_format_percent() -> None:
    """パーセントフォーマットのテスト。"""
    result = pytilpack.babel.format_percent(0.25, locale="en")
    assert "25" in result
    assert "%" in result


def test_format_decimal() -> None:
    """小数フォーマットのテスト。"""
    result = pytilpack.babel.format_decimal(3.14159, format="#.##", locale="en")
    assert result == "3.14"
