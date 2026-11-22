import pathlib

import fastapi
import fastapi.testclient

import pytilpack.fastapi.i18n
import pytilpack.i18n

LOCALES_DIR = pathlib.Path(__file__).parent.parent / "fixtures" / "locales"


def _create_app() -> fastapi.FastAPI:
    app = fastapi.FastAPI()

    @app.get("/hello")
    def hello() -> dict[str, str]:
        return {"message": pytilpack.i18n.gettext_func("Hello")}

    state = pytilpack.i18n.I18nState(LOCALES_DIR, locales=["en", "ja"], default_locale="ja")
    app.add_middleware(pytilpack.fastapi.i18n.I18nMiddleware, state=state)
    return app


def test_accept_language_ja() -> None:
    app = _create_app()
    with fastapi.testclient.TestClient(app) as client:
        response = client.get("/hello", headers={"Accept-Language": "ja"})
        assert response.status_code == 200
        assert response.json() == {"message": "こんにちは"}


def test_accept_language_en() -> None:
    app = _create_app()
    with fastapi.testclient.TestClient(app) as client:
        default_response = client.get("/hello")
        assert default_response.status_code == 200
        assert default_response.json() == {"message": "こんにちは"}

        response = client.get("/hello", headers={"Accept-Language": "en"})
        assert response.status_code == 200
        assert response.json() == {"message": "Hello"}


def test_accept_language_quality() -> None:
    app = _create_app()
    with fastapi.testclient.TestClient(app) as client:
        response = client.get("/hello", headers={"Accept-Language": "ja;q=0.8,en;q=0.9"})
        assert response.status_code == 200
        assert response.json() == {"message": "Hello"}
