"""FastAPI関連のその他のユーティリティ。"""

import json
import typing

import fastapi.encoders
import starlette.responses


class JSONResponse(starlette.responses.Response):
    """インデント付きJSONを返すFastAPIのresponse_class。

    デフォルトのJSONResponseはインデントなしでJSONを返すが、
    このクラスはindent=2のインデント付きで返す。
    Pydanticモデルやdatetime等もfastapi.encoders.jsonable_encoderで変換する。

    Usage:
        @app.get("/pretty", response_class=pytilpack.fastapi.JSONResponse)
        def pretty():
            return {"message": "indented JSON"}

        @app.get("/model", response_model=MyModel, response_class=pytilpack.fastapi.JSONResponse)
        def model():
            return MyModel(field="value")

    """

    media_type = "application/json"

    def render(self, content: typing.Any) -> bytes:
        """コンテンツをインデント付きJSONのバイト列に変換する。"""
        encoded = fastapi.encoders.jsonable_encoder(content)
        return json.dumps(encoded, ensure_ascii=False, indent=2, separators=(", ", ": ")).encode("utf-8")
