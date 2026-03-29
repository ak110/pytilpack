"""Quart i18nのテスト。"""

import pathlib

import pytest
import quart

import pytilpack.i18n
import pytilpack.quart.i18n

LOCALES_DIR = pathlib.Path(__file__).parent.parent / "fixtures" / "locales"


@pytest.fixture(name="app")
def _app() -> quart.Quart:
    app = quart.Quart(__name__)
    app.config["TESTING"] = True
    pytilpack.quart.i18n.init_app(app, LOCALES_DIR, default_locale="en")

    @app.route("/hello")
    async def hello() -> str:
        """翻訳テスト用エンドポイント。"""
        return pytilpack.i18n.gettext_func("Hello")

    @app.route("/template")
    async def template() -> str:
        """テンプレート翻訳テスト用エンドポイント。"""
        return await quart.render_template_string("{{ _('Hello') }}")

    return app


@pytest.mark.asyncio
async def test_accept_language_ja(app: quart.Quart) -> None:
    """Accept-Language: jaでリクエストすると日本語翻訳が返る。"""
    async with app.test_client() as client:
        response = await client.get("/hello", headers={"Accept-Language": "ja"})
        assert response.status_code == 200
        data = await response.get_data(as_text=True)
        assert data == "こんにちは"


@pytest.mark.asyncio
async def test_accept_language_en(app: quart.Quart) -> None:
    """Accept-Language: enでリクエストするとフォールバック（原文）が返る。"""
    async with app.test_client() as client:
        response = await client.get("/hello", headers={"Accept-Language": "en"})
        assert response.status_code == 200
        data = await response.get_data(as_text=True)
        assert data == "Hello"


@pytest.mark.asyncio
async def test_accept_language_default(app: quart.Quart) -> None:
    """Accept-Languageなしではデフォルトロケール（en）が使われる。"""
    async with app.test_client() as client:
        response = await client.get("/hello")
        assert response.status_code == 200
        data = await response.get_data(as_text=True)
        assert data == "Hello"


@pytest.mark.asyncio
async def test_jinja2_template(app: quart.Quart) -> None:
    """Jinja2テンプレートで_()が使える。"""
    async with app.test_client() as client:
        response = await client.get("/template", headers={"Accept-Language": "ja"})
        assert response.status_code == 200
        data = await response.get_data(as_text=True)
        assert data == "こんにちは"
