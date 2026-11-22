import asyncio
import typing

import pytest
import pytest_asyncio
import quart
import quart.typing
import quart_auth

import pytilpack.quart
import pytilpack.quart_auth


class User(pytilpack.quart_auth.UserMixin):
    def __init__(self, name: str, is_admin: bool = False) -> None:
        self.name = name
        self.is_admin = is_admin


def _add_admin_routes(app: quart.Quart) -> None:

    @app.route("/admin")
    @pytilpack.quart_auth.admin_only
    async def admin():
        return "admin page"

    @app.route("/admin-sync")
    @pytilpack.quart_auth.admin_only
    def admin_sync():
        return "admin sync page"

    @app.route("/login_admin")
    async def login_admin():
        pytilpack.quart_auth.login_user("admin1")
        return "admin logged in"


@pytest.fixture(name="app", scope="module")
def _app() -> quart.Quart:
    app = quart.Quart(__name__)
    app.secret_key = "secret"

    auth_manager = pytilpack.quart_auth.QuartAuth[User]()
    app.config["QUART_AUTH_COOKIE_SECURE"] = False
    auth_manager.init_app(app)

    users = {"user1": User("test user"), "admin1": User("admin user", is_admin=True)}

    @auth_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return users.get(user_id)

    assert auth_manager.user_loader_func is not None

    @app.route("/public")
    async def public():
        return "public page"

    @app.route("/login")
    async def login():
        pytilpack.quart_auth.login_user("user1")
        return "logged in"

    @app.route("/logout")
    async def logout():
        pytilpack.quart_auth.logout_user()
        return "logged out"

    @app.route("/private")
    @quart_auth.login_required
    async def private():
        return "private page"

    @app.route("/user")
    async def user():
        return await quart.render_template_string(
            "User: {{ current_user.name if current_user.is_authenticated else '<anonymous>' }}"
        )

    _add_admin_routes(app)

    @app.route("/login_no_cookie")
    async def login_no_cookie():
        pytilpack.quart_auth.login_user("user1", set_cookie=False)
        assert pytilpack.quart_auth.is_authenticated(), "直後はログイン済みにはなる"
        _ = await pytilpack.quart_auth.acurrent_user()
        return "logged in without cookie"

    # arid: disable
    @app.route("/auser")
    async def auser():
        user = await pytilpack.quart_auth.acurrent_user()
        if user.is_authenticated:
            assert isinstance(user, User)
            return f"async user: {user.name}"
        return "async user: anonymous"

    @app.route("/ais_admin")
    async def ais_admin_route():
        result = await pytilpack.quart_auth.ais_admin()
        return f"is_admin: {result}"

    # arid: enable
    return app


@pytest_asyncio.fixture(name="client", scope="function")
async def _client(
    app: quart.Quart,
) -> typing.AsyncGenerator[quart.typing.TestClientProtocol, None]:
    async with app.test_client() as client:
        yield client


@pytest.mark.asyncio
async def test_public_access(client: quart.typing.TestClientProtocol) -> None:
    response = await client.get("/public")
    assert response.status_code == 200
    assert await response.get_data(as_text=True) == "public page"


@pytest.mark.asyncio
async def test_private_access_unauthorized(
    client: quart.typing.TestClientProtocol,
) -> None:
    response = await client.get("/private")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_private_access_authorized(
    client: quart.typing.TestClientProtocol,
) -> None:
    async with client.session_transaction():
        response = await client.get("/login")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "logged in"

        response = await client.get("/private")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "private page"


@pytest.mark.asyncio
async def test_current_user_anonymous(client: quart.typing.TestClientProtocol) -> None:
    response = await client.get("/user")
    text = await response.get_data(as_text=True)
    assert text == "User: &lt;anonymous&gt;"


@pytest.mark.asyncio
async def test_current_user_authenticated(
    client: quart.typing.TestClientProtocol,
) -> None:
    async with client.session_transaction():
        response = await client.get("/login")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "logged in"

        response = await client.get("/user")
        text = await response.get_data(as_text=True)
        assert text == "User: test user"


@pytest.mark.asyncio
async def test_logout(client: quart.typing.TestClientProtocol) -> None:
    async with client.session_transaction():
        response = await client.get("/login")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "logged in"

        response = await client.get("/logout")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "logged out"

        response = await client.get("/user")
        text = await response.get_data(as_text=True)
        assert text == "User: &lt;anonymous&gt;"


@pytest.mark.asyncio
async def test_admin_only(client: quart.typing.TestClientProtocol) -> None:
    response = await client.get("/admin")
    assert response.status_code == 401

    response = await client.get("/admin-sync")
    assert response.status_code == 401

    async with client.session_transaction():
        response = await client.get("/login")
        assert response.status_code == 200

        response = await client.get("/admin")
        assert response.status_code == 403

        response = await client.get("/admin-sync")
        assert response.status_code == 403

    async with client.session_transaction():
        response = await client.get("/login_admin")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "admin logged in"

        response = await client.get("/admin")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "admin page"

        response = await client.get("/admin-sync")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "admin sync page"

    @pytilpack.quart_auth.admin_only
    async def test_async_function() -> str:
        """非同期テスト関数。"""
        return "test"

    @pytilpack.quart_auth.admin_only
    def test_sync_function() -> str:
        """同期テスト関数。"""
        return "test"

    assert test_async_function.__name__ == "test_async_function"
    assert test_async_function.__doc__ == "非同期テスト関数。"

    assert test_sync_function.__name__ == "test_sync_function"
    assert test_sync_function.__doc__ == "同期テスト関数。"


@pytest.mark.asyncio
async def test_login_user_set_cookie_false(
    client: quart.typing.TestClientProtocol,
) -> None:
    response = await client.get("/login_no_cookie")
    assert response.status_code == 200
    assert await response.get_data(as_text=True) == "logged in without cookie"
    assert "Set-Cookie" not in response.headers

    response = await client.get("/user")
    text = await response.get_data(as_text=True)
    assert text == "User: &lt;anonymous&gt;"

    response = await client.get("/private")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_acurrent_user(client: quart.typing.TestClientProtocol) -> None:
    response = await client.get("/auser")
    assert response.status_code == 200
    assert await response.get_data(as_text=True) == "async user: anonymous"

    async with client.session_transaction():
        response = await client.get("/login")
        assert response.status_code == 200

        response = await client.get("/auser")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "async user: test user"


@pytest.mark.asyncio
async def test_ais_admin(client: quart.typing.TestClientProtocol) -> None:
    response = await client.get("/ais_admin")
    assert await response.get_data(as_text=True) == "is_admin: False"

    async with client.session_transaction():
        await client.get("/login")
        response = await client.get("/ais_admin")
        assert await response.get_data(as_text=True) == "is_admin: False"

    async with client.session_transaction():
        await client.get("/login_admin")
        response = await client.get("/ais_admin")
        assert await response.get_data(as_text=True) == "is_admin: True"

    async with client.session_transaction():
        await client.get("/login_admin")
        response = await client.get("/admin")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "admin page"


@pytest.fixture(name="app_async", scope="module")
def _app_async() -> quart.Quart:
    app = quart.Quart(__name__)
    app.secret_key = "secret"

    auth_manager = pytilpack.quart_auth.QuartAuth[User]()
    app.config["QUART_AUTH_COOKIE_SECURE"] = False
    auth_manager.init_app(app)

    users = {"user1": User("async test user"), "admin1": User("async admin user", is_admin=True)}

    @auth_manager.user_loader
    async def load_user(user_id: str) -> User | None:
        await asyncio.sleep(0.01)
        return users.get(user_id)

    assert auth_manager.auser_loader_func is not None

    @app.before_request
    async def before_request() -> None:
        await pytilpack.quart_auth.ensure_user_loaded()

    @app.route("/public")
    async def public():
        return "public page"

    @app.route("/login")
    async def login():
        pytilpack.quart_auth.login_user("user1")
        return "logged in"

    @app.route("/user")
    async def user():
        return await quart.render_template_string(
            "User: {{ current_user.name if current_user.is_authenticated else '<anonymous>' }}"
        )

    @app.route("/private")
    @quart_auth.login_required
    async def private():
        return "private page"

    _add_admin_routes(app)

    @app.route("/login_no_cookie")
    async def login_no_cookie():
        pytilpack.quart_auth.login_user("user1", set_cookie=False)
        await pytilpack.quart_auth.ensure_user_loaded()
        return "logged in without cookie"

    # arid: disable
    @app.route("/auser")
    async def auser():
        user = await pytilpack.quart_auth.acurrent_user()
        if user.is_authenticated:
            assert isinstance(user, User)
            return f"async user: {user.name}"
        return "async user: anonymous"

    @app.route("/ais_admin")
    async def ais_admin_route():
        result = await pytilpack.quart_auth.ais_admin()
        return f"is_admin: {result}"

    # arid: enable
    return app


@pytest_asyncio.fixture(name="client_async", scope="function")
async def _client_async(
    app_async: quart.Quart,
) -> typing.AsyncGenerator[quart.typing.TestClientProtocol, None]:
    async with app_async.test_client() as client:
        yield client


@pytest.mark.asyncio
async def test_async_user_loader_anonymous(client_async: quart.typing.TestClientProtocol) -> None:
    response = await client_async.get("/user")
    text = await response.get_data(as_text=True)
    assert text == "User: &lt;anonymous&gt;"


@pytest.mark.asyncio
async def test_async_user_loader_authenticated(
    client_async: quart.typing.TestClientProtocol,
) -> None:
    async with client_async.session_transaction():
        response = await client_async.get("/login")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "logged in"

        response = await client_async.get("/user")
        text = await response.get_data(as_text=True)
        assert text == "User: async test user"


@pytest.mark.asyncio
async def test_async_user_loader_private_access(
    client_async: quart.typing.TestClientProtocol,
) -> None:
    async with client_async.session_transaction():
        response = await client_async.get("/login")
        assert response.status_code == 200

        response = await client_async.get("/private")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "private page"


@pytest.mark.asyncio
async def test_async_login_no_cookie_no_set_cookie(client_async: quart.typing.TestClientProtocol) -> None:
    response = await client_async.get("/login_no_cookie")
    assert response.status_code == 200
    assert await response.get_data(as_text=True) == "logged in without cookie"
    assert "Set-Cookie" not in response.headers


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["/admin", "/admin-sync"])
async def test_async_user_loader_admin_only(client_async: quart.typing.TestClientProtocol, route: str) -> None:
    response = await client_async.get(route)
    assert response.status_code == 401

    async with client_async.session_transaction():
        await client_async.get("/login")
        response = await client_async.get(route)
        assert response.status_code == 403

    async with client_async.session_transaction():
        response = await client_async.get("/login_admin")
        assert response.status_code == 200

        response = await client_async.get(route)
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == ("admin page" if route == "/admin" else "admin sync page")


@pytest.mark.asyncio
async def test_async_acurrent_user(client_async: quart.typing.TestClientProtocol) -> None:
    response = await client_async.get("/auser")
    assert response.status_code == 200
    assert await response.get_data(as_text=True) == "async user: anonymous"

    async with client_async.session_transaction():
        await client_async.get("/login")
        response = await client_async.get("/auser")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "async user: async test user"


@pytest.mark.asyncio
async def test_async_ais_admin(client_async: quart.typing.TestClientProtocol) -> None:
    response = await client_async.get("/ais_admin")
    assert await response.get_data(as_text=True) == "is_admin: False"

    async with client_async.session_transaction():
        await client_async.get("/login_admin")
        response = await client_async.get("/ais_admin")
        assert await response.get_data(as_text=True) == "is_admin: True"


@pytest.mark.asyncio
async def test_template_context_fallback_without_before_request() -> None:
    app = quart.Quart(__name__)
    app.secret_key = "secret"

    auth_manager = pytilpack.quart_auth.QuartAuth[User]()
    auth_manager.init_app(app)

    @auth_manager.user_loader
    async def load_user(user_id: str) -> User | None:
        del user_id  # noqa
        return None

    @app.route("/test")
    async def test_page():
        if hasattr(quart.g, "quart_auth_current_user"):
            delattr(quart.g, "quart_auth_current_user")
        return await quart.render_template_string(
            "User: {{ current_user.name if current_user.is_authenticated else '<anonymous>' }}"
        )

    async with app.test_client() as client:
        response = await client.get("/test")
        assert response.status_code == 200
        text = await response.get_data(as_text=True)
        assert text == "User: &lt;anonymous&gt;"
