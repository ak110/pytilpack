"""Quart-Auth関連のユーティリティのテスト。"""

import typing

import pytest
import pytest_asyncio
import quart
import quart_auth

import pytilpack.quart_auth_


class User(pytilpack.quart_auth_.UserMixin):
    """テスト用ユーザーモデル。"""

    def __init__(self, name: str) -> None:
        self.name = name


@pytest.fixture(name="app", scope="module")
def _app() -> quart.Quart:
    """テスト用アプリケーション。"""
    app = quart.Quart(__name__)
    app.secret_key = "secret"  # 暗号化に必要

    # Quart-Authの設定
    auth_manager = pytilpack.quart_auth_.QuartAuth[User]()
    auth_manager.init_app(app)

    # ユーザーローダーの設定
    users = {"user1": User("test user")}

    @auth_manager.user_loader
    async def load_user(user_id: str) -> User | None:
        return users.get(user_id)

    assert auth_manager.user_loader_func is not None

    # テスト用ルート
    @app.route("/public")
    async def public():
        return "public page"

    @app.route("/login")
    async def login():
        # ログイン処理
        pytilpack.quart_auth_.login_user("user1")
        return "logged in"

    @app.route("/logout")
    async def logout():
        # ログアウト処理
        pytilpack.quart_auth_.logout_user()
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

    return app


@pytest_asyncio.fixture(name="client", scope="function")
async def _client(
    app: quart.Quart,
) -> typing.AsyncGenerator[quart.typing.TestClientProtocol, None]:
    """テスト用クライアント。"""
    async with app.test_client() as client:
        yield client


@pytest.mark.asyncio
async def test_public_access(client: quart.typing.TestClientProtocol) -> None:
    """未ログイン状態でも公開ページにアクセスできる。"""
    response = await client.get("/public")
    assert response.status_code == 200
    assert await response.get_data(as_text=True) == "public page"


@pytest.mark.asyncio
async def test_private_access_unauthorized(
    client: quart.typing.TestClientProtocol,
) -> None:
    """未ログイン状態で非公開ページにアクセスするとリダイレクトされる。"""
    response = await client.get("/private")
    assert response.status_code == 401  # 未認証


@pytest.mark.asyncio
async def test_private_access_authorized(
    client: quart.typing.TestClientProtocol,
) -> None:
    """ログイン状態で非公開ページにアクセスできる。"""
    async with client.session_transaction():
        # ログイン
        response = await client.get("/login")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "logged in"

        # 非公開ページにアクセス
        response = await client.get("/private")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "private page"


@pytest.mark.asyncio
async def test_current_user_anonymous(client: quart.typing.TestClientProtocol) -> None:
    """未ログイン状態ではcurrent_userが匿名ユーザーになる。"""
    response = await client.get("/user")
    text = await response.get_data(as_text=True)
    assert text == "User: &lt;anonymous&gt;"


@pytest.mark.asyncio
async def test_current_user_authenticated(
    client: quart.typing.TestClientProtocol,
) -> None:
    """ログイン状態ではcurrent_userが認証済みユーザーになる。"""
    async with client.session_transaction():
        # ログイン
        response = await client.get("/login")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "logged in"

        response = await client.get("/user")
        text = await response.get_data(as_text=True)
        assert text == "User: test user"


@pytest.mark.asyncio
async def test_logout(client: quart.typing.TestClientProtocol) -> None:
    """ログアウト後はcurrent_userが匿名ユーザーに戻る。"""
    async with client.session_transaction():
        # ログイン
        response = await client.get("/login")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "logged in"

        # ログアウト
        response = await client.get("/logout")
        assert response.status_code == 200
        assert await response.get_data(as_text=True) == "logged out"

        response = await client.get("/user")
        text = await response.get_data(as_text=True)
        assert text == "User: &lt;anonymous&gt;"
