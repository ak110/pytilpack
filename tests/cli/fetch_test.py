"""ローカルHTTP応答だけを使ってfetchのCLIを実行する。"""

import flask
import pytest

import pytilpack.flask
from pytilpack.cli.main import main


def test_fetch_cli(capsys: pytest.CaptureFixture[str]) -> None:
    """取得したHTMLを簡略化して標準出力へ返す。"""
    app = flask.Flask(__name__)

    @app.get("/")
    def page() -> str:
        return "<html><body><main><h1>ローカル応答</h1><p>取得する本文</p></main></body></html>"

    with pytilpack.flask.run(app, port=0) as port:
        main(["fetch", f"http://127.0.0.1:{port}/"])
    output = capsys.readouterr().out
    assert "ローカル応答" in output
    assert "取得する本文" in output
