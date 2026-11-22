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
        return pytilpack.i18n.gettext_func("Hello")

    @app.route("/template")
    async def template() -> str:
        return await quart.render_template_string("{{ _('Hello') }}")

    return app


@pytest.mark.asyncio
async def test_accept_language_ja(app: quart.Quart) -> None:
    async with app.test_client() as client:
        response = await client.get("/hello", headers={"Accept-Language": "ja"})
        assert response.status_code == 200
        data = await response.get_data(as_text=True)
        assert data == "こんにちは"


@pytest.mark.asyncio
async def test_accept_language_en(app: quart.Quart) -> None:
    async with app.test_client() as client:
        response = await client.get("/hello", headers={"Accept-Language": "en"})
        assert response.status_code == 200
        data = await response.get_data(as_text=True)
        assert data == "Hello"


@pytest.mark.asyncio
async def test_accept_language_default(app: quart.Quart) -> None:
    async with app.test_client() as client:
        response = await client.get("/hello")
        assert response.status_code == 200
        data = await response.get_data(as_text=True)
        assert data == "Hello"


@pytest.mark.asyncio
async def test_jinja2_template(app: quart.Quart) -> None:
    async with app.test_client() as client:
        response = await client.get("/template", headers={"Accept-Language": "ja"})
        assert response.status_code == 200
        data = await response.get_data(as_text=True)
        assert data == "こんにちは"


@pytest.mark.asyncio
async def test_i18n_state_deactivated_after_request() -> None:
    app = quart.Quart(__name__)
    states: list[bool] = []

    @app.teardown_request
    async def observe_locale(error: BaseException | None) -> None:
        del error
        states.append(pytilpack.i18n.is_active())

    pytilpack.quart.i18n.init_app(app, LOCALES_DIR, default_locale="en")

    @app.route("/hello")
    async def hello() -> str:
        assert pytilpack.i18n.is_active()
        return pytilpack.i18n.gettext_func("Hello")

    client = app.test_client()
    response = await client.get("/hello", headers={"Accept-Language": "ja"})
    assert response.status_code == 200

    assert states
    assert not any(states)
