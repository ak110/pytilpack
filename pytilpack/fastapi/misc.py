"""FastAPI関連のその他のユーティリティ。"""

import json
import typing

import starlette.responses


class JSONResponse(starlette.responses.Response):
    """インデント付きJSONを返すFastAPIのresponse_class。

    デフォルトのJSONResponseはインデントなしでJSONを返すが、
    このクラスはindent=2のインデント付きで返す。

    Usage:
        @app.get("/pretty", response_class=JSONResponse)
        def pretty():
            return {"message": "indented JSON"}

    """

    media_type = "application/json"

    def render(self, content: typing.Any) -> bytes:
        """コンテンツをインデント付きJSONのバイト列に変換する。"""
        return json.dumps(content, ensure_ascii=False, indent=2, separators=(", ", ": ")).encode("utf-8")
