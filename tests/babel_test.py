"""babelのテスト。"""

import datetime
import pathlib
import typing

import pytest

import pytilpack.babel
import pytilpack.i18n

LOCALES_DIR = pathlib.Path(__file__).parent / "fixtures" / "locales"


@pytest.fixture(name="i18n_ja")
def _i18n_ja() -> typing.Generator[None, None, None]:
    """日本語ロケールをアクティブにするフィクスチャ。"""
    state = pytilpack.i18n.I18nState(LOCALES_DIR, default_locale="ja")
    tokens = pytilpack.i18n.activate(state, "ja")
    yield
    pytilpack.i18n.deactivate(tokens)


@pytest.mark.usefixtures("i18n_ja")
def test_format() -> None:
    """babel各種フォーマット関数のテスト。"""
    # format_date: I18nState経由のロケールでフォーマット
    date = datetime.date(2024, 1, 15)
    result = pytilpack.babel.format_date(date, format="long")
    assert "2024" in result
    assert "1" in result
    assert "15" in result

    # format_datetime: ロケール直指定
    dt = datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)
    result = pytilpack.babel.format_datetime(dt, format="short", locale="en")
    assert "1/15/24" in result

    # format_time
    t = datetime.time(14, 30, 0)
    result = pytilpack.babel.format_time(t, format="short", locale="ja")
    assert "14:30" in result

    # format_number
    assert pytilpack.babel.format_number(1234567, locale="en") == "1,234,567"
    result_ja = pytilpack.babel.format_number(1234567, locale="ja")
    assert "1,234,567" in result_ja

    # format_currency
    result = pytilpack.babel.format_currency(1234, "JPY", locale="ja")
    assert "1,234" in result
    assert "￥" in result or "¥" in result

    # format_percent
    result = pytilpack.babel.format_percent(0.25, locale="en")
    assert "25" in result
    assert "%" in result

    # format_decimal
    result = pytilpack.babel.format_decimal(3.14159, format="#.##", locale="en")
    assert result == "3.14"
