"""データURL関連。

<https://developer.mozilla.org/ja/docs/Web/URI/Schemes/data>

"""

import base64
import dataclasses
import typing
import urllib.parse


@dataclasses.dataclass
class DataURL:
    """データURLを扱うクラス。"""

    data: bytes
    mime_type: str = ""
    encoding: typing.Literal["base64", "plain"] = "base64"

    def to_url(self) -> str:
        """データURLを文字列として返す。"""
        if self.encoding == "base64":
            b64 = base64.b64encode(self.data).decode("ascii")
            return f"data:{self.mime_type};base64,{b64}"
        else:
            encoded_data = urllib.parse.quote(self.data.decode("utf-8"))
            return f"data:{self.mime_type},{encoded_data}"


def create(mime_type: str, data: bytes) -> str:
    """小さい画像などのバイナリデータをURLに埋め込んだものを作って返す。

    Args:
        mime_type: 例：'image/png'
        data: 埋め込むデータ

    """
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{b64}"


def parse(data_url: str) -> DataURL:
    """データURLからデータ部分を取り出して返す。

    Args:
        data_url: 'data:image/png;base64,....'

    """
    if not data_url.startswith("data:") or "," not in data_url:
        raise ValueError("Invalid data URL: " + data_url[:32] + ("" if len(data_url) <= 32 else "..."))
    prefix, content = data_url.split(",", 1)
    prefix = prefix.removeprefix("data:")
    encoding: typing.Literal["base64", "plain"]
    if prefix.endswith(";base64"):
        mime_type = prefix.removesuffix(";base64")
        encoding = "base64"
        data = base64.b64decode(content)
    else:
        mime_type = prefix
        encoding = "plain"
        data = urllib.parse.unquote(content).encode("utf-8")
    if mime_type == "":
        mime_type = "text/plain"
    return DataURL(mime_type=mime_type, encoding=encoding, data=data)


def get_base64_data(data_url: str) -> str:
    """データURLからbase64エンコードされたデータ部分を取り出して返す。

    Args:
        data_url: 'data:image/png;base64,....'

    """
    header, body = data_url.split(",", 1)
    if header.endswith(";base64"):
        return body
    # base64ではない場合はURLデコードしてからbase64エンコードする
    decoded = urllib.parse.unquote(body).encode("utf-8")
    return base64.b64encode(decoded).decode("ascii")
