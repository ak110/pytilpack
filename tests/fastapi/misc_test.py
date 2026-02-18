"""FastAPI miscのテスト。"""

import json

import fastapi
import fastapi.testclient
import pydantic
import pytest

import pytilpack.fastapi


class _Item(pydantic.BaseModel):
    name: str
    value: int


@pytest.fixture(name="app")
def _app() -> fastapi.FastAPI:
    app = fastapi.FastAPI()

    @app.get("/pretty", response_class=pytilpack.fastapi.JSONResponse)
    def pretty():
        return {"message": "hello", "value": 42, "items": [1, 2, 3]}

    @app.get("/pretty-japanese", response_class=pytilpack.fastapi.JSONResponse)
    def japanese():
        return {"メッセージ": "こんにちは"}

    @app.get("/model", response_class=pytilpack.fastapi.JSONResponse, response_model=_Item)
    def model():
        return _Item(name="test", value=123)

    return app


@pytest.fixture(name="client")
def _client(app: fastapi.FastAPI) -> fastapi.testclient.TestClient:
    return fastapi.testclient.TestClient(app)


def test_json_response(client: fastapi.testclient.TestClient) -> None:
    """JSONResponseのテスト。"""
    response = client.get("/pretty")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    text = response.text
    # インデント付きであることを確認
    assert "\n" in text
    assert "  " in text

    # 内容が正しいことを確認
    data = json.loads(text)
    assert data == {"message": "hello", "value": 42, "items": [1, 2, 3]}


def test_json_response_ensure_ascii(client: fastapi.testclient.TestClient) -> None:
    """ensure_ascii=Falseで日本語がそのまま出力されることを確認するテスト。"""
    response = client.get("/pretty-japanese")

    assert response.status_code == 200
    assert "メッセージ" in response.text
    assert "こんにちは" in response.text


def test_json_response_pydantic_model(client: fastapi.testclient.TestClient) -> None:
    """response_modelにPydanticモデルを指定した場合のテスト。"""
    response = client.get("/model")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    text = response.text
    assert "\n" in text

    data = json.loads(text)
    assert data == {"name": "test", "value": 123}
