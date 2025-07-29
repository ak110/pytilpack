"""疑似乱数関連。"""


def xor_shift32(x: int) -> int:
    """ステートレス32ビットXOR Shift。"""
    x &= 0xFFFFFFFF
    x ^= (x << 13) & 0xFFFFFFFF
    x ^= x >> 17
    x ^= (x << 5) & 0xFFFFFFFF
    return x


def wang_hash32(x: int) -> int:
    """Wang hash。

    <https://gist.github.com/badboy/6267743>
    """
    x = (x ^ 61) ^ (x >> 16)
    x = x + (x << 3)
    x = x ^ (x >> 4)
    x = x * 0x27D4EB2D
    x = x ^ (x >> 15)
    return x & 0xFFFFFFFF
