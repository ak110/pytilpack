"""単独Web extraの隔離環境でpytestなしのassertsを実行する。"""

import asyncio
import importlib
import importlib.abc
import importlib.util
import inspect
import sys

import httpx


class _NoFcntl(importlib.abc.MetaPathFinder):
    """Flaskのimport時にUnix専用モジュールを利用できなくする。"""

    def find_spec(self, fullname, path, target=None):
        # MetaPathFinderの公開署名を保ち、対象以外は後続finderへ渡す。
        del path, target
        if fullname == "fcntl":
            raise ImportError("fcntlを利用できないプラットフォームの検証")


def main() -> None:
    """HTML・JSON・XML・bytes・SSEとステータスの公開アサーションを呼ぶ。"""
    extra = sys.argv[1]
    assert importlib.util.find_spec("pytest") is None
    if extra == "flask":
        sys.meta_path.insert(0, _NoFcntl())
    module = importlib.import_module(f"pytilpack.{extra}")

    def response(body, content_type):
        if extra == "fastapi":
            return httpx.Response(200, content=body, headers={"Content-Type": content_type})
        framework = importlib.import_module(extra)
        return framework.Response(body, content_type=content_type)

    def call(name, value):
        result = getattr(module, name)(value)
        return asyncio.run(result) if inspect.isawaitable(result) else result

    html = "<!doctype html><html><head><title>確認</title></head><body>成功</body></html>"
    assert call("assert_html", response(html, "text/html")) == html
    assert call("assert_json", response('{"ok":true}', "application/json")) == {"ok": True}
    assert call("assert_xml", response("<root />", "application/xml")) == "<root />"
    assert call("assert_bytes", response(b"body", "application/octet-stream")) == b"body"
    call("assert_sse", response("data: body\n\n", "text/event-stream"))
    call("assert_response", response("body", "text/plain"))
    assert importlib.util.find_spec("pytest") is None
    print(f"{extra}: pytestなしのimportと全asserts呼出し成功")


if __name__ == "__main__":
    main()
