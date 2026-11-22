import datetime as dt
import pathlib
import typing

import babel.dates
import babel.numbers
import pytest

import pytilpack.babel
import pytilpack.i18n

LOCALES_DIR = pathlib.Path(__file__).parent / "fixtures" / "locales"


@pytest.fixture(name="i18n_ja")
def _i18n_ja() -> typing.Generator[None, None, None]:
    state = pytilpack.i18n.I18nState(LOCALES_DIR, default_locale="ja")
    tokens = pytilpack.i18n.activate(state, "ja")
    yield
    pytilpack.i18n.deactivate(tokens)


@pytest.mark.usefixtures("i18n_ja")
def test_format() -> None:
    date = dt.date(2024, 1, 15)
    assert pytilpack.babel.format_date(date, format="long") == babel.dates.format_date(date, format="long", locale="ja")
    assert pytilpack.babel.format_date(date, format="long", locale="en") == babel.dates.format_date(
        date, format="long", locale="en"
    )

    value = dt.datetime(2024, 1, 15, 10, 30, 0, tzinfo=dt.UTC)
    offset = dt.timezone(dt.timedelta(hours=-11))
    assert pytilpack.babel.format_datetime(value, format="MM/dd/yyyy HH:mm", locale="en", tzinfo=offset) == ("01/14/2024 23:30")

    t = dt.time(14, 30, 0)
    result = pytilpack.babel.format_time(t, format="short", locale="ja")
    assert "14:30" in result

    assert pytilpack.babel.format_number(1234567, locale="en") == "1,234,567"
    assert pytilpack.babel.format_number(1234567, locale="de") == babel.numbers.format_decimal(1234567, locale="de")

    result = pytilpack.babel.format_currency(1234, "JPY", locale="ja")
    assert "1,234" in result
    assert "￥" in result or "¥" in result

    result = pytilpack.babel.format_percent(0.25, locale="en")
    assert "25" in result
    assert "%" in result

    result = pytilpack.babel.format_decimal(3.14159, format="#.##", locale="en")
    assert result == "3.14"
