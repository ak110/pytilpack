import asyncio
import pathlib

import pytest

import pytilpack.i18n

LOCALES_DIR = pathlib.Path(__file__).parent / "fixtures" / "locales"


def test_i18n_state_init() -> None:
    state = pytilpack.i18n.I18nState(LOCALES_DIR, default_locale="en")
    assert "ja" in state.supported_locales
    assert state.domain == "messages"
    assert state.default_locale == "en"


def test_i18n_state_explicit_locales() -> None:
    state = pytilpack.i18n.I18nState(LOCALES_DIR, locales=["ja"], default_locale="en")
    assert state.supported_locales == ["ja"]


def test_activate_deactivate() -> None:
    state = pytilpack.i18n.I18nState(LOCALES_DIR, default_locale="en")
    assert not pytilpack.i18n.is_active()
    tokens = pytilpack.i18n.activate(state, "ja")
    try:
        assert pytilpack.i18n.is_active()
        assert pytilpack.i18n.get_locale() == "ja"
        assert pytilpack.i18n.get_state() is state
    finally:
        pytilpack.i18n.deactivate(tokens)
    assert not pytilpack.i18n.is_active()


def test_gettext() -> None:
    state = pytilpack.i18n.I18nState(LOCALES_DIR, default_locale="en")
    tokens = pytilpack.i18n.activate(state, "ja")
    try:
        assert pytilpack.i18n.gettext_func("Hello") == "こんにちは"
        assert pytilpack.i18n._("Hello") == "こんにちは"
        assert pytilpack.i18n.gettext_func("Goodbye") == "さようなら"
        msg = pytilpack.i18n.gettext_func("Hello, %(name)s!") % {"name": "太郎"}
        assert msg == "こんにちは、太郎さん！"
        assert pytilpack.i18n.ngettext("%(num)d item", "%(num)d items", 1) % {"num": 1} == "1個のアイテム"
        assert pytilpack.i18n.ngettext("%(num)d item", "%(num)d items", 5) % {"num": 5} == "5個のアイテム"
        assert pytilpack.i18n.pgettext("greeting", "Hello") == "ご挨拶"
    finally:
        pytilpack.i18n.deactivate(tokens)


def test_get_state_without_activate() -> None:
    with pytest.raises(RuntimeError, match="I18nStateが未設定"):
        pytilpack.i18n.get_state()


def test_set_locale() -> None:
    state = pytilpack.i18n.I18nState(LOCALES_DIR, default_locale="en")
    tokens = pytilpack.i18n.activate(state, "en")
    try:
        assert pytilpack.i18n.gettext_func("Hello") == "Hello"
        pytilpack.i18n.set_locale("ja")
        assert pytilpack.i18n.gettext_func("Hello") == "こんにちは"
    finally:
        pytilpack.i18n.deactivate(tokens)


@pytest.mark.asyncio
async def test_locale_isolation_between_tasks() -> None:
    state = pytilpack.i18n.I18nState(LOCALES_DIR, default_locale="en")
    activated = asyncio.Barrier(2)
    translated = asyncio.Barrier(2)

    async def translate(locale: str) -> str:
        tokens = pytilpack.i18n.activate(state, locale)
        try:
            await activated.wait()
            result = pytilpack.i18n.gettext_func("Hello")
            await translated.wait()
            return result
        finally:
            pytilpack.i18n.deactivate(tokens)

    async with asyncio.timeout(5):
        ja, en = await asyncio.gather(translate("ja"), translate("en"))
        assert ja == "こんにちは"
        assert en == "Hello"
