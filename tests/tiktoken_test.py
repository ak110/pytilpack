import base64
import fractions
import io
import itertools
import math
import sys
import typing
import warnings

import httpx
import openai.types.chat
import PIL.Image
import pytest
import tiktoken

import pytilpack.tiktoken

ALL_MODELS = [
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-0613",
    "gpt-3.5-turbo-16k-0613",
    "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo-0125",
    "gpt-4",
    "gpt-4-0613",
    "gpt-4-32k-0613",
    "gpt-4-1106-preview",
    "gpt-4-0125-preview",
    "gpt-4-1106-vision-preview",
    "gpt-4-turbo-2024-04-09",
    "gpt-4o-mini",
    "gpt-4o-mini-2024-07-18",
    "gpt-4o",
    "gpt-4o-2024-05-13",
    "gpt-4o-2024-08-06",
    "o1-mini",
    "o1-mini-2024-09-12",
    "o1-preview",
    "o1-preview-2024-09-12",
    "o1",
    "o1-2024-12-17",
    "o3-mini",
    "o3-mini-2025-01-31",
    "o4-mini",
    "o4-mini-2025-04-16",
    "gpt-4.1-nano",
    "gpt-4.1-mini",
    "gpt-4.1",
    "gpt-4.1-nano-2025-04-14",
    "gpt-4.1-mini-2025-04-14",
    "gpt-4.1-2025-04-14",
]


_WEATHER_TOOL: openai.types.chat.ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": "Get the current weather in a given location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g. San Francisco, CA",
                },
                "unit": {
                    "type": "string",
                    "description": "The unit of temperature to return",
                    "enum": ["celsius", "fahrenheit"],
                },
            },
            "required": ["location"],
        },
    },
}


def test_get_encoding_for_model(monkeypatch: pytest.MonkeyPatch) -> None:
    encodings = {
        name: tiktoken.Encoding(name, pat_str=".", mergeable_ranks={b"a": 0}, special_tokens={})
        for name in ("cl100k_base", "o200k_base")
    }

    def get_encoding(name: str) -> tiktoken.Encoding:
        return encodings[name]

    monkeypatch.setattr(tiktoken.model, "get_encoding", get_encoding)
    monkeypatch.setattr(tiktoken, "get_encoding", get_encoding)
    assert pytilpack.tiktoken.get_encoding_for_model("gpt-3.5-turbo-0613").name == "cl100k_base"
    assert pytilpack.tiktoken.get_encoding_for_model("unknown-model").name == "o200k_base"


def test_num_tokens_from_messages():
    assert (
        pytilpack.tiktoken.num_tokens_from_messages(
            "gpt-3.5-turbo-0613",
            [
                {"role": "system", "content": "てすと"},
                {"role": "user", "content": "1+1=?"},
            ],
        )
        == 18
    )


def test_num_tokens_from_texts():
    assert pytilpack.tiktoken.num_tokens_from_texts("gpt-3.5-turbo-0613", "2") == 1

    assert pytilpack.tiktoken.num_tokens_from_texts("gpt-4-turbo-2024-04-09", "1+1=2です。") == 7


@pytest.mark.parametrize(
    "model,expected",
    [("gpt-3.5-turbo", 105), ("gpt-4", 105), ("gpt-4o", 101), ("gpt-4o-mini", 101)],
)
def test_num_tokens_from_messages_with_tools(model: str, expected: int):
    num_tokens = pytilpack.tiktoken.num_tokens_from_messages(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that can answer to questions about the weather.",
            },
            {"role": "user", "content": "What's the weather like in San Francisco?"},
        ],
        tools=[_WEATHER_TOOL],
    )
    assert num_tokens == expected


# litellmが依存するfastuuidは3.15用のwheelを公開しておらず、ソースからもビルドできない（PyO3が3.14までの対応）。
# このためlitellmは開発依存で3.15未満に限定しており、比較テストも3.15未満だけで定義する。
# fastuuidが3.15へ対応したら、pyproject.tomlの環境マーカーと併せてこの分岐を外す。
if sys.version_info < (3, 15):
    import litellm.types.llms.openai  # ty: ignore[import-not-found]
    import litellm.utils  # ty: ignore[import-not-found]

    @pytest.mark.parametrize("model", ALL_MODELS)
    def test_vs_litellm(model: str):
        messages: list[openai.types.chat.ChatCompletionMessageParam] = [
            {"role": "system", "content": "てすと"},
            {"role": "user", "content": "1+1=？"},
            {"role": "assistant", "content": "2です。"},
            {"role": "user", "content": "2+2=？"},
        ]

        actual_tokens = pytilpack.tiktoken.num_tokens_from_messages(model=model, messages=messages, tools=None)
        litellm_tokens = litellm.utils.token_counter(model=model, messages=messages, tools=None)
        assert actual_tokens == litellm_tokens, "ツールなしトークン数の不一致"

        tools: list[openai.types.chat.ChatCompletionToolParam] | None = [_WEATHER_TOOL]
        actual_tokens = pytilpack.tiktoken.num_tokens_from_messages(model=model, messages=messages, tools=tools)
        litellm_tokens = litellm.utils.token_counter(
            model=model,
            messages=messages,
            tools=typing.cast(list[litellm.types.llms.openai.ChatCompletionToolParam], tools),
        )

        # LiteLLMは現在以下のモデルがgpt-3.5-turboなどと同じ扱いになっている
        # (おそらく不具合)
        if actual_tokens != litellm_tokens and model in [
            "o1-mini",
            "o1-mini-2024-09-12",
            "o1-preview",
            "o1-preview-2024-09-12",
            "o4-mini",
            "o4-mini-2025-04-16",
            "gpt-4.1-nano",
            "gpt-4.1-mini",
            "gpt-4.1",
            "gpt-4.1-nano-2025-04-14",
            "gpt-4.1-mini-2025-04-14",
            "gpt-4.1-2025-04-14",
        ]:
            warnings.warn("LiteLLMのバグのため対症療法", UserWarning, stacklevel=1)
            litellm_tokens = litellm.utils.token_counter(
                model="gpt-4o",
                messages=messages,
                tools=typing.cast(list[litellm.types.llms.openai.ChatCompletionToolParam], tools),
            )

        assert actual_tokens == litellm_tokens, "ツールありトークン数の不一致"


_VISION_MODEL = "gpt-4o-2024-08-06"


def _image_tokens(url: str, detail: typing.Literal["low", "high", "auto"]) -> int:
    return pytilpack.tiktoken.num_tokens_from_messages(
        _VISION_MODEL,
        [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": url, "detail": detail}}]}],
    )


@pytest.mark.parametrize(
    "width,height,tiles",
    [
        (512, 512, 1),
        (513, 512, 2),
        (768, 1000, 4),
        (1024, 1024, 4),
        (4096, 2048, 6),
        (1600, 1600, 4),
        (4096, 512, 4),
        (1, 2052, 4),
        (514, 2052, 8),
    ],
)
def test_calculate_high_detail_image_token_cost(width: int, height: int, tiles: int) -> None:
    buffer = io.BytesIO()
    with PIL.Image.new("1", (width, height)) as image:
        image.save(buffer, format="PNG")
    url = f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode('ascii')}"
    assert _image_tokens(url, "high") - _image_tokens(url, "low") == 170 * tiles


def test_high_detail_image_token_cost_at_resize_boundaries() -> None:
    dimensions = (range(1, 5), range(511, 515), range(767, 771), range(2047, 2053), range(4095, 4101))
    boundary_cases = itertools.product(tuple(itertools.chain.from_iterable(dimensions)), repeat=2)
    narrow_cases = ((1, long) for long in range(1, 4001))
    tall_cases = ((long, 1) for long in range(2, 4001))
    for width, height in itertools.chain(boundary_cases, narrow_cases, tall_cases):
        scale = min(fractions.Fraction(1), fractions.Fraction(2048, max(width, height)))
        short, long = sorted((width * scale, height * scale))
        if short > 768:
            long = fractions.Fraction(math.floor(long * 768 / short))
            short = fractions.Fraction(768)
        tiles = math.ceil(short / 512) * math.ceil(long / 512)
        expected = 85 + 170 * tiles
        actual = pytilpack.tiktoken._calculate_high_detail_image_token_cost(width, height)  # pylint: disable=protected-access
        assert actual == expected


def test_calculate_image_token_cost_without_dims(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_dimension_lookup(*args: object, **kwargs: object) -> typing.NoReturn:
        raise AssertionError("Image dimensions are not needed")

    monkeypatch.setattr(httpx, "get", unexpected_dimension_lookup)
    monkeypatch.setattr(PIL.Image, "open", unexpected_dimension_lookup)
    url = "https://example.com/a.png"
    encoding = tiktoken.encoding_for_model(_VISION_MODEL)
    without_image = pytilpack.tiktoken.num_tokens_from_messages(_VISION_MODEL, [{"role": "user", "content": []}])
    assert _image_tokens(url, "low") - without_image - len(encoding.encode("image_url")) == 85
    with pytest.raises(ValueError):
        _image_tokens(url, typing.cast(typing.Literal["low"], "invalid"))
