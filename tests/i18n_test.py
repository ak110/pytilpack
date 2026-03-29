"""i18nのテスト。"""

import asyncio
import pathlib

import pytest

import pytilpack.i18n

LOCALES_DIR = pathlib.Path(__file__).parent / "fixtures" / "locales"


@pytest.fixture(autouse=True)
def _cleanup_context() -> None:  # type: ignore[misc]
    """テストごとにContextVarをリセットする。"""
    yield  # type: ignore[misc]
    # ContextVarのデフォルト値に戻すため、新しいTokenでresetはできないので
    # テスト間の影響を防ぐためにyield後は何もしない


def test_i18n_state_init() -> None:
    """I18nStateの初期化テスト。"""
    state = pytilpack.i18n.I18nState(LOCALES_DIR, default_locale="en")
    assert "ja" in state.supported_locales
    assert state.domain == "messages"
    assert state.default_locale == "en"


def test_i18n_state_explicit_locales() -> None:
    """明示的なロケール指定のテスト。"""
    state = pytilpack.i18n.I18nState(LOCALES_DIR, locales=["ja"], default_locale="en")
    assert state.supported_locales == ["ja"]


def test_activate_deactivate() -> None:
    """activate/deactivateのテスト。"""
    state = pytilpack.i18n.I18nState(LOCALES_DIR, default_locale="en")
    tokens = pytilpack.i18n.activate(state, "ja")
    try:
        assert pytilpack.i18n.get_locale() == "ja"
        assert pytilpack.i18n.get_state() is state
    finally:
        pytilpack.i18n.deactivate(tokens)


def test_gettext() -> None:
    """翻訳関数のテスト。"""
    state = pytilpack.i18n.I18nState(LOCALES_DIR, default_locale="en")
    tokens = pytilpack.i18n.activate(state, "ja")
    try:
        # 基本翻訳
        assert pytilpack.i18n.gettext_func("Hello") == "こんにちは"
        assert pytilpack.i18n._("Hello") == "こんにちは"
        assert pytilpack.i18n.gettext_func("Goodbye") == "さようなら"
        # パラメータ埋め込み
        msg = pytilpack.i18n.gettext_func("Hello, %(name)s!") % {"name": "太郎"}
        assert msg == "こんにちは、太郎さん！"
        # 複数形
        assert pytilpack.i18n.ngettext("%(num)d item", "%(num)d items", 1) % {"num": 1} == "1個のアイテム"
        assert pytilpack.i18n.ngettext("%(num)d item", "%(num)d items", 5) % {"num": 5} == "5個のアイテム"
        # コンテキスト付き翻訳
        assert pytilpack.i18n.pgettext("greeting", "Hello") == "ご挨拶"
    finally:
        pytilpack.i18n.deactivate(tokens)


def test_gettext_fallback() -> None:
    """翻訳がない場合のフォールバックテスト。"""
    state = pytilpack.i18n.I18nState(LOCALES_DIR, default_locale="en")
    tokens = pytilpack.i18n.activate(state, "en")
    try:
        # 英語の翻訳ファイルがないのでそのまま返される
        assert pytilpack.i18n.gettext_func("Hello") == "Hello"
    finally:
        pytilpack.i18n.deactivate(tokens)


def test_get_state_without_activate() -> None:
    """activate()なしでget_state()を呼ぶとRuntimeError。"""
    with pytest.raises(RuntimeError, match="I18nStateが未設定"):
        pytilpack.i18n.get_state()


def test_set_locale() -> None:
    """set_localeで動的にロケールを切り替える。"""
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
    """asyncioタスク間でロケールが独立していることを確認する。"""
    state = pytilpack.i18n.I18nState(LOCALES_DIR, default_locale="en")
    results: dict[str, str] = {}

    async def task_ja() -> None:
        tokens = pytilpack.i18n.activate(state, "ja")
        try:
            await asyncio.sleep(0.01)
            results["ja"] = pytilpack.i18n.gettext_func("Hello")
        finally:
            pytilpack.i18n.deactivate(tokens)

    async def task_en() -> None:
        tokens = pytilpack.i18n.activate(state, "en")
        try:
            await asyncio.sleep(0.01)
            results["en"] = pytilpack.i18n.gettext_func("Hello")
        finally:
            pytilpack.i18n.deactivate(tokens)

    await asyncio.gather(task_ja(), task_en())
    assert results["ja"] == "こんにちは"
    assert results["en"] == "Hello"
