"""tiktoken関連のユーティリティ集。"""

import base64
import io
import logging
import math
import re

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
        logger.warning(f"model '{model_name}' not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    return encoding


def num_tokens_from_messages(
    model: str, messages: list[openai.types.chat.ChatCompletionMessageParam], tools=None
) -> int:
    """メッセージからトークン数を算出。

    <https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb>

    Args:
        model: モデル名。
        messages: メッセージのリスト。
        tools: function callingの情報。

    Returns:
        トークン数。

    """
    encoding = get_encoding_for_model(model)
    if model in {
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k-0613",
        "gpt-3.5-turbo-1106",
        "gpt-3.5-turbo-0125",
        "gpt-4-0613",
        "gpt-4-32k-0613",
        "gpt-4-1106-preview",
        "gpt-4-0125-preview",
        "gpt-4-vision-preview",
        "gpt-4-turbo-2024-04-09",
    }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif "gpt-3.5-turbo" in model:
        return num_tokens_from_messages("gpt-3.5-turbo-0613", messages)
    elif "gpt-4" in model:
        return num_tokens_from_messages("gpt-4-turbo-2024-04-09", messages)
    else:
        logger.error(
            f"num_tokens_from_messages() is not implemented for model {model}."
            " See https://github.com/openai/openai-python/blob/main/chatml.md"
            " for information on how messages are converted to tokens."
        )
        return num_tokens_from_messages("gpt-3.5-turbo-0613", messages)
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
            tool_call: openai.types.chat.ChatCompletionMessageToolCallParam
            for tool_call in tool_calls:  # type: ignore[attr-defined]
                if (function := tool_call.get("function")) is not None:
                    num_tokens += len(encoding.encode(function["name"]))
                    num_tokens += len(encoding.encode(function["arguments"]))

    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>

    if tools is not None:
        num_tokens += num_tokens_from_tools(encoding, tools)

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


def _get_image_dims(image):
    # regex to check if image is a URL or base64 string
    url_regex = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
    if re.match(url_regex, image):
        response = httpx.get(image)
        response.raise_for_status()
        response.read()
        image = PIL.Image.open(io.BytesIO(response.content))
        return image.size
    elif re.match(r"data:image\/\w+;base64", image):
        image = re.sub(r"data:image\/\w+;base64,", "", image)
        image = PIL.Image.open(io.BytesIO(base64.b64decode(image)))
        return image.size
    else:
        raise ValueError("Image must be a URL or base64 string.")


def num_tokens_from_texts(model: str, texts: list[str] | str) -> int:
    """テキストからトークン数を算出。"""
    if isinstance(texts, str):
        texts = [texts]
    enc = get_encoding_for_model(model)
    return sum(len(enc.encode(text)) for text in texts)


def num_tokens_from_tools(encoding, tools) -> int:
    """Function calling部分のトークン数算出。

    <https://community.openai.com/t/how-to-calculate-the-tokens-when-using-function-call/266573/10>

    """
    num_tokens = 0
    for function in tools:
        function = function.get("function", function)
        try:
            function_tokens = len(encoding.encode(function["name"]))
            function_tokens += len(encoding.encode(function["description"]))

            if "parameters" in function:
                parameters = function["parameters"]
                if "properties" in parameters:
                    for properties_key in parameters["properties"]:
                        function_tokens += len(encoding.encode(properties_key))
                        v = parameters["properties"][properties_key]
                        for field in v:
                            if field == "type":
                                function_tokens += 2
                                function_tokens += len(encoding.encode(v["type"]))
                            elif field == "description":
                                function_tokens += 2
                                function_tokens += len(
                                    encoding.encode(v["description"])
                                )
                            elif field == "enum":
                                function_tokens -= 3
                                for o in v["enum"]:
                                    function_tokens += 3
                                    function_tokens += len(encoding.encode(o))
                            else:
                                logger.warning(f"not supported field {field}")
                    function_tokens += 11

            num_tokens += function_tokens
        except Exception:
            logger.exception("Failed to calculate tokens from tools.", exc_info=True)

    num_tokens += 12
    return num_tokens
