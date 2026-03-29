"""FastAPI i18nのテスト。"""

import pathlib

import fastapi
import fastapi.testclient

import pytilpack.fastapi.i18n
import pytilpack.i18n

LOCALES_DIR = pathlib.Path(__file__).parent.parent / "fixtures" / "locales"


def _create_app() -> fastapi.FastAPI:
    """テスト用FastAPIアプリを作成する。"""
    app = fastapi.FastAPI()

    @app.get("/hello")
    def hello() -> dict[str, str]:
        """翻訳テスト用エンドポイント。"""
        return {"message": pytilpack.i18n.gettext_func("Hello")}

    # ミドルウェアを追加
    state = pytilpack.i18n.I18nState(LOCALES_DIR, default_locale="en")
    app.add_middleware(pytilpack.fastapi.i18n.I18nMiddleware, state=state)
    return app


def test_accept_language_ja() -> None:
    """Accept-Language: jaでリクエストすると日本語翻訳が返る。"""
    app = _create_app()
    with fastapi.testclient.TestClient(app) as client:
        response = client.get("/hello", headers={"Accept-Language": "ja"})
        assert response.status_code == 200
        assert response.json() == {"message": "こんにちは"}


def test_accept_language_en() -> None:
    """Accept-Language: enでリクエストするとフォールバック（原文）が返る。"""
    app = _create_app()
    with fastapi.testclient.TestClient(app) as client:
        response = client.get("/hello", headers={"Accept-Language": "en"})
        assert response.status_code == 200
        assert response.json() == {"message": "Hello"}


def test_accept_language_default() -> None:
    """Accept-Languageなしではデフォルトロケール（en）が使われる。"""
    app = _create_app()
    with fastapi.testclient.TestClient(app) as client:
        response = client.get("/hello")
        assert response.status_code == 200
        assert response.json() == {"message": "Hello"}


def test_accept_language_quality() -> None:
    """quality値に基づいたロケール選択のテスト。"""
    app = _create_app()
    with fastapi.testclient.TestClient(app) as client:
        response = client.get("/hello", headers={"Accept-Language": "en;q=0.8,ja;q=0.9"})
        assert response.status_code == 200
        assert response.json() == {"message": "こんにちは"}
