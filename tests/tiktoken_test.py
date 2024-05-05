"""テストコード。"""

import pytilpack.tiktoken_


def test_get_encoding_for_model():
    """get_encoding_for_model()のテスト。"""
    encoding = pytilpack.tiktoken_.get_encoding_for_model("gpt-3.5-turbo-0613")
    assert encoding is not None

    encoding = pytilpack.tiktoken_.get_encoding_for_model("unknown-model")
    assert encoding is not None


def test_num_tokens_from_messages():
    assert (
        pytilpack.tiktoken_.num_tokens_from_messages(
            "gpt-3.5-turbo-0613",
            [
                {"role": "system", "content": "てすと"},
                {"role": "user", "content": "1+1=?"},
            ],
        )
        == 18
    )


def test_num_tokens_from_texts():
    """num_tokens_from_texts()のテスト。"""
    assert pytilpack.tiktoken_.num_tokens_from_texts("gpt-3.5-turbo-0613", "2") == 1

    assert (
        pytilpack.tiktoken_.num_tokens_from_texts(
            "gpt-4-turbo-2024-04-09", "1+1=2です。"
        )
        == 7
    )


def test_num_tokens_from_tools():
    """num_tokens_from_tools()のテスト。"""
    encoding = pytilpack.tiktoken_.get_encoding_for_model("gpt-3.5-turbo-0613")

    tools = [
        {
            "name": "tool1",
            "description": "description1",
            "parameters": {
                "properties": {
                    "prop1": {"type": "type1", "description": "desc1"},
                    "prop2": {"type": "type2", "description": "desc2"},
                }
            },
        }
    ]
    num_tokens = pytilpack.tiktoken_.num_tokens_from_tools(encoding, tools)
    assert num_tokens == 47
