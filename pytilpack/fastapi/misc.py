__lazy_modules__ = ["fastapi.encoders", "json", "starlette.responses", "typing"]

import json
import typing

import fastapi.encoders
import starlette.responses

__all__ = ["JSONResponse"]


class JSONResponse(starlette.responses.Response):
    media_type = "application/json"  # type: ignore[assignment]

    def render(self, content: typing.Any) -> bytes:
        encoded = fastapi.encoders.jsonable_encoder(content)
        return json.dumps(encoded, ensure_ascii=False, indent=2, separators=(", ", ": ")).encode("utf-8")
