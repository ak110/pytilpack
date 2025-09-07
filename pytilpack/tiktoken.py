"""tiktoken関連のユーティリティ集。"""

import base64
import io
import logging
import math
import re
import typing
import warnings

import httpx
import openai.types.chat
import PIL.Image
import tiktoken

logger = logging.getLogger(__name__)


def get_encoding_for_model(model_name: str) -> tiktoken.Encoding:
    """モデル名からtiktokenのEncodingを取得する。"""
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        logger.warning(f"model '{model_name}' not found. Using o200k_base encoding.")
        encoding = tiktoken.get_encoding("o200k_base")
    return encoding


def num_tokens_from_messages(
    model: str,
    messages: list[openai.types.chat.ChatCompletionMessageParam],
    tools: list[openai.types.chat.ChatCompletionToolParam] | None = None,
    tool_choice: openai.types.chat.ChatCompletionNamedToolChoiceParam | None = None,
) -> int:
    """メッセージからトークン数を算出。

    <https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb>

    Args:
        model: モデル名。
        messages: メッセージのリスト。
        tools: function callingの情報。
        tool_choice: ツール選択の情報。

    Returns:
        トークン数。

    """
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

    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>

    if tools is not None:
        num_tokens += num_tokens_for_tools(model, tools, tool_choice, encoding=encoding)

    return num_tokens


def _calculate_image_token_cost(image: str, detail: str) -> int:
    # Constants
    LOW_DETAIL_COST = 85
    HIGH_DETAIL_COST_PER_TILE = 170
    ADDITIONAL_COST = 85

    if detail == "low":
        # Low detail images have a fixed cost
        return LOW_DETAIL_COST
    elif detail in ("high", "auto"):  # autoのときどうなるか不明のため安全側に倒す
        # Calculate token cost for high detail images
        width, height = _get_image_dims(image)
        # Check if resizing is needed to fit within a 2048 x 2048 square
        if max(width, height) > 2048:
            # Resize the image to fit within a 2048 x 2048 square
            ratio = 2048 / max(width, height)
            width = int(width * ratio)
            height = int(height * ratio)

        # Further scale down to 768px on the shortest side
        if min(width, height) > 768:
            ratio = 768 / min(width, height)
            width = int(width * ratio)
            height = int(height * ratio)
        # Calculate the number of 512px squares
        num_squares = math.ceil(width / 512) * math.ceil(height / 512)

        # Calculate the total token cost
        total_cost = num_squares * HIGH_DETAIL_COST_PER_TILE + ADDITIONAL_COST

        return total_cost
    else:
        # Invalid detail_option
        raise ValueError("Invalid detail_option. Use 'low' or 'high'.")


def _get_image_dims(image: str) -> tuple[int, int]:
    # regex to check if image is a URL or base64 string
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
    """テキストからトークン数を算出。"""
    if isinstance(texts, str):
        texts = [texts]
    enc = get_encoding_for_model(model)
    return sum(len(enc.encode(text)) for text in texts)


def num_tokens_from_tools(encoding: tiktoken.Encoding, tools: list[openai.types.chat.ChatCompletionToolParam]) -> int:
    warnings.warn(
        "num_tokens_from_tools is deprecated. Use num_tokens_for_tools instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return num_tokens_for_tools(model="gpt-4o", tools=tools, encoding=encoding)


def num_tokens_for_tools(
    model: str,
    tools: list[openai.types.chat.ChatCompletionToolParam],
    tool_choice: openai.types.chat.ChatCompletionToolChoiceOptionParam | None = None,
    encoding: tiktoken.Encoding | None = None,
) -> int:
    """Function calling部分のトークン数算出。

    <https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb>
    <https://community.openai.com/t/how-to-calculate-the-tokens-when-using-function-call/266573/10>

    """
    if len(tools) == 0:
        return 0

    if encoding is None:
        encoding = get_encoding_for_model(model)

    if "gpt-3.5-" in model or "gpt-4-" in model or model == "gpt-4":
        # gpt-3.5-turbo, gpt-4, gpt-4-turboまで
        func_init = 10
        prop_init = 3
        prop_key = 3
        enum_init = -3
        enum_item = 3
        func_end = 12
    else:
        # gpt-4o, o1など以降
        func_init = 7
        prop_init = 3
        prop_key = 3
        enum_init = -3
        enum_item = 3
        func_end = 12

    num_tokens = 0
    for tool in tools:
        if tool.get("type") != "function":
            logger.warning(f"Tool type {tool.get('type')} is not supported. Only 'function' type is supported.")
            continue
        function = tool["function"]
        try:
            num_tokens += func_init
            print(f"{num_tokens=} func_init")

            func_name = function["name"]
            func_desc = function.get("description", "")
            if func_desc.endswith("."):
                func_desc = func_desc[:-1]
            num_tokens += len(encoding.encode(f"{func_name}:{func_desc}"))
            print(f"{num_tokens=} func")

            parameters = function.get("parameters", {})
            properties = typing.cast(dict[str, dict[str, typing.Any]], parameters.get("properties", {}))
            if len(properties) > 0:
                num_tokens += prop_init
                print(f"{num_tokens=} prop_init")
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
            logger.exception("Failed to calculate tokens from tools.", exc_info=True)
    num_tokens += func_end

    # If tool_choice is 'none', add one token.
    # If it's an object, add 4 + the number of tokens in the function name.
    # If it's undefined or 'auto', don't add anything.
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
