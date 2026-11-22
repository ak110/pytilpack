import pathlib

import flask
import pytest

import pytilpack.flask
from pytilpack.cli.main import main

_HTML = "<html><body><header>見出し</header><main><h1>ローカル応答</h1><p>取得する本文</p></main></body></html>"


def _app() -> flask.Flask:
    app = flask.Flask(__name__)

    @app.get("/")
    def page() -> str:
        return _HTML

    @app.get("/csv")
    def csv() -> flask.Response:
        return flask.Response("a,b\n1,2\n", content_type="text/csv")

    @app.get("/bin")
    def binary() -> flask.Response:
        return flask.Response(b"\x00\x01", content_type="application/octet-stream")

    return app


def test_fetch_cli(capsys: pytest.CaptureFixture[str]) -> None:
    with pytilpack.flask.run(_app(), port=0) as port:
        main(["fetch", f"http://127.0.0.1:{port}/"])
    captured = capsys.readouterr()
    assert "ローカル応答" in captured.out
    assert "取得する本文" in captured.out
    assert "見出し" not in captured.out
    assert "HTTP Request" not in captured.err


def test_fetch_cli_raw_output_document(tmp_path: pathlib.Path) -> None:
    output = tmp_path / "out.html"
    with pytilpack.flask.run(_app(), port=0) as port:
        main(["fetch", "--raw", "-O", str(output), f"http://127.0.0.1:{port}/"])
    assert output.read_text(encoding="utf-8") == _HTML


def test_fetch_cli_text(capsys: pytest.CaptureFixture[str]) -> None:
    with pytilpack.flask.run(_app(), port=0) as port:
        main(["fetch", f"http://127.0.0.1:{port}/csv"])
    assert capsys.readouterr().out == "a,b\n1,2\n\n"


def test_fetch_cli_unsupported(capsys: pytest.CaptureFixture[str]) -> None:
    with pytilpack.flask.run(_app(), port=0) as port, pytest.raises(SystemExit) as exc_info:
        main(["fetch", f"http://127.0.0.1:{port}/bin"])
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "Content-Type: application/octet-stream" in err
    assert len(err.strip().splitlines()) == 1
