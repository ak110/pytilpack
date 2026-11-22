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
        return {"メッセージ": "こんにちは", "nested": {"items": [42]}}

    @app.get("/model", response_class=pytilpack.fastapi.JSONResponse, response_model=_Item)
    def model():
        return _Item(name="test", value=123)

    @app.get("/direct-model")
    def direct_model():
        return pytilpack.fastapi.JSONResponse(_Item(name="test", value=123))

    return app


@pytest.fixture(name="client")
def _client(app: fastapi.FastAPI) -> fastapi.testclient.TestClient:
    return fastapi.testclient.TestClient(app)


def test_json_response(client: fastapi.testclient.TestClient) -> None:
    response = client.get("/pretty")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    assert json.loads(response.content) == {"メッセージ": "こんにちは", "nested": {"items": [42]}}
    assert "こんにちは".encode() in response.content
    assert "メッセージ".encode() in response.content
    assert {'  "nested": {', '    "items": [', "      42"} <= {line.rstrip() for line in response.text.splitlines()}


@pytest.mark.parametrize("path", ["/model", "/direct-model"])
def test_json_response_pydantic_model(client: fastapi.testclient.TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    text = response.text
    assert "\n" in text

    data = json.loads(text)
    assert data == {"name": "test", "value": 123}
