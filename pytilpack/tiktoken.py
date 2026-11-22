__lazy_modules__ = [
    "PIL.Image",
    "base64",
    "httpx",
    "io",
    "logging",
    "math",
    "openai.types.chat",
    "pytilpack.python",
    "re",
    "tiktoken",
    "typing",
]

import base64
import io
import logging
import math
import re
import typing

import httpx
import openai.types.chat
import PIL.Image
import tiktoken

import pytilpack.python

logger = logging.getLogger(__name__)


def get_encoding_for_model(model_name: str) -> tiktoken.Encoding:
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        logger.warning(
            f"model '{model_name}' not found. Using o200k_base encoding and continuing."
            " No action is needed if the approximation is acceptable; otherwise pass a model name known to tiktoken."
        )
        encoding = tiktoken.get_encoding("o200k_base")
    return encoding


def num_tokens_from_messages(
    model: str,
    messages: list[openai.types.chat.ChatCompletionMessageParam],
    tools: list[openai.types.chat.ChatCompletionToolParam] | None = None,
    tool_choice: openai.types.chat.ChatCompletionNamedToolChoiceParam | None = None,
) -> int:
    encoding = get_encoding_for_model(model)

    tokens_per_message = 3
    tokens_per_name = 1

    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message

        if (role := message.get("role")) is not None:
            num_tokens += len(encoding.encode(role))

        if (name := message.get("name")) is not None:
            assert isinstance(name, str)
            num_tokens += len(encoding.encode(name))
            num_tokens += tokens_per_name

        if (content := message.get("content")) is not None:
            if isinstance(content, str):
                num_tokens += len(encoding.encode(content))
            else:
                for item in content:
                    num_tokens += len(encoding.encode(item["type"]))
                    if item["type"] == "text":
                        num_tokens += len(encoding.encode(item["text"]))
                    elif item["type"] == "image_url":
                        num_tokens += _calculate_image_token_cost(
                            item["image_url"]["url"],
                            item["image_url"].get("detail", "auto"),
                        )

        if (tool_calls := message.get("tool_calls")) is not None:
            for tool_call in tool_calls:  # type: ignore[attr-defined]
                if tool_call.get("type") == "function" and (function := tool_call.get("function")) is not None:
                    num_tokens += len(encoding.encode(function.get("name", "")))
                    num_tokens += len(encoding.encode(function.get("arguments", "")))
                elif tool_call.get("type") == "custom" and (custom := tool_call.get("custom")) is not None:
                    num_tokens += len(encoding.encode(custom.get("name", "")))
                    num_tokens += len(encoding.encode(custom.get("input", "")))

    num_tokens += 3

    if tools is not None:
        num_tokens += num_tokens_for_tools(model, tools, tool_choice, encoding=encoding)

    return num_tokens


def _calculate_image_token_cost(image: str, detail: str) -> int:
    if detail == "low":
        return 85
    elif detail in ("high", "auto"):  # auto のときどうなるか不明のため安全側の判定とする
        width, height = _get_image_dims(image)
        return _calculate_high_detail_image_token_cost(width, height)
    else:
        raise ValueError("Invalid detail_option. Use 'low' or 'high'.")


def _calculate_high_detail_image_token_cost(width: int, height: int) -> int:
    if max(width, height) > 2048:
        ratio = 2048 / max(width, height)
        width = int(width * ratio)
        height = int(height * ratio)
    if min(width, height) > 768:
        ratio = 768 / min(width, height)
        width = int(width * ratio)
        height = int(height * ratio)
    num_squares = math.ceil(width / 512) * math.ceil(height / 512)
    return num_squares * 170 + 85


def _get_image_dims(image: str) -> tuple[int, int]:
    url_regex = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
    if re.match(url_regex, image):
        response = httpx.get(image)
        response.raise_for_status()
        response.read()
        return PIL.Image.open(io.BytesIO(response.content)).size
    elif re.match(r"data:image\/\w+;base64", image):
        image = re.sub(r"data:image\/\w+;base64,", "", image)
        return PIL.Image.open(io.BytesIO(base64.b64decode(image))).size
    else:
        raise ValueError("Image must be a URL or base64 string.")


def num_tokens_from_texts(model: str, texts: list[str] | str) -> int:
    if isinstance(texts, str):
        texts = [texts]
    enc = get_encoding_for_model(model)
    return sum(len(enc.encode(text)) for text in texts)


@pytilpack.python.deprecated("Use pytilpack.tiktoken.num_tokens_for_tools instead.")
def num_tokens_from_tools(encoding: tiktoken.Encoding, tools: list[openai.types.chat.ChatCompletionToolParam]) -> int:
    return num_tokens_for_tools(model="gpt-4o", tools=tools, encoding=encoding)


def num_tokens_for_tools(
    model: str,
    tools: list[openai.types.chat.ChatCompletionToolParam],
    tool_choice: openai.types.chat.ChatCompletionToolChoiceOptionParam | None = None,
    encoding: tiktoken.Encoding | None = None,
) -> int:
    if len(tools) == 0:
        return 0

    if encoding is None:
        encoding = get_encoding_for_model(model)

    prop_init = 3
    prop_key = 3
    enum_init = -3
    enum_item = 3
    func_end = 12
    func_init = 10 if "gpt-3.5-" in model or "gpt-4-" in model or model == "gpt-4" else 7

    num_tokens = 0
    for tool in tools:
        if tool.get("type") != "function":
            logger.warning(
                f"Tool type {tool.get('type')} is not supported. Only 'function' type is supported."
                " Excluded this tool from the token count and continued."
            )
            continue
        function = tool["function"]
        try:
            num_tokens += func_init

            func_name = function["name"]
            func_desc = function.get("description", "")
            if func_desc.endswith("."):
                func_desc = func_desc[:-1]
            num_tokens += len(encoding.encode(f"{func_name}:{func_desc}"))

            parameters = function.get("parameters", {})
            properties = typing.cast(dict[str, dict[str, typing.Any]], parameters.get("properties", {}))
            if len(properties) > 0:
                num_tokens += prop_init
                for prop_name, fields in properties.items():
                    num_tokens += prop_key

                    prop_type = fields.get("type", "")
                    prop_desc = fields.get("description", "")
                    num_tokens += len(encoding.encode(f"{prop_name}:{prop_type}:{prop_desc}"))

                    if "enum" in fields:
                        num_tokens += enum_init
                        for item in fields["enum"]:
                            num_tokens += enum_item
                            num_tokens += len(encoding.encode(item))

        except Exception:
            logger.exception(
                "Failed to calculate tokens from tools. Excluded the rest of this tool from the token count and continued;"
                " check that the tool definition follows the function tool schema.",
                exc_info=True,
            )
    num_tokens += func_end

    if tool_choice == "none":
        num_tokens += 1
    elif isinstance(tool_choice, dict):
        num_tokens += 7
        if tool_choice.get("type") == "function":
            num_tokens += len(
                encoding.encode(
                    str(
                        typing.cast(openai.types.chat.ChatCompletionNamedToolChoiceParam, tool_choice)
                        .get("function", {})
                        .get("name", "")
                    )
                )
            )
        elif tool_choice.get("type") == "custom":
            num_tokens += len(
                encoding.encode(
                    str(
                        typing.cast(openai.types.chat.ChatCompletionNamedToolChoiceCustomParam, tool_choice)
                        .get("custom", {})
                        .get("name", "")
                    )
                )
            )

    return num_tokens
