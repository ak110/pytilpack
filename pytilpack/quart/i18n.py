"""Quart用i18n統合。"""

import pathlib

import quart

import pytilpack.http
import pytilpack.i18n


def init_app(
    app: quart.Quart,
    locale_dir: str | pathlib.Path,
    domain: str = "messages",
    supported_locales: list[str] | None = None,
    default_locale: str = "en",
    fallback: bool = True,
) -> None:
    """Quartアプリにi18nを統合する。

    before_requestでAccept-Languageからロケールを自動設定し、
    Jinja2テンプレートに翻訳関数を登録する。

    Args:
        app: Quartアプリ
        locale_dir: localeディレクトリのパス
        domain: gettextドメイン名
        supported_locales: サポートするロケール一覧
        default_locale: デフォルトロケール
        fallback: フォールバック有無

    """
    # I18nStateを作成してextensionsに格納
    state = pytilpack.i18n.I18nState(
        locale_dir=locale_dir,
        domain=domain,
        locales=supported_locales,
        default_locale=default_locale,
        fallback=fallback,
    )
    app.extensions["pytilpack_i18n"] = state

    # Jinja2テンプレートに翻訳関数を登録
    app.jinja_env.globals["_"] = pytilpack.i18n.gettext_func
    app.jinja_env.globals["ngettext"] = pytilpack.i18n.ngettext

    @app.before_request
    async def _set_locale_from_request() -> None:
        i18n_state: pytilpack.i18n.I18nState = app.extensions["pytilpack_i18n"]
        # Accept-Languageからロケールを決定
        accept_lang = quart.request.headers.get("Accept-Language", "")
        locale = pytilpack.http.select_accept_language(
            accept_lang,
            i18n_state.supported_locales,
            default=i18n_state.default_locale,
        )
        pytilpack.i18n.activate(i18n_state, locale)
