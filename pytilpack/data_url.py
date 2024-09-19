"""データURL関連。

<https://developer.mozilla.org/ja/docs/Web/URI/Schemes/data>

"""

import base64
import dataclasses
import urllib.parse


@dataclasses.dataclass
class DataURL:
    """データURLを扱うクラス。"""

    mime_type: str
    encoding: str
    data: bytes


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
        raise ValueError(
            "Invalid data URL: "
            + data_url[:32]
            + ("" if len(data_url) <= 32 else "...")
        )
    prefix, content = data_url.split(",", 1)
    prefix = prefix.removeprefix("data:")
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
