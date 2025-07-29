"""テストコード。"""

import pytilpack.random


def test_xor_shift32() -> None:
    """xor_shift32のテスト。"""
    results = [pytilpack.random.xor_shift32(i) for i in range(100)]

    # 固定値のテスト
    assert results[0] == 0
    assert results[1] == 270369
    assert pytilpack.random.xor_shift32(0xFFFFFFFF) == 253983

    # 同じ入力には同じ出力
    results2 = [pytilpack.random.xor_shift32(i) for i in range(len(results))]
    assert results == results2

    # 出力が32ビット範囲であることの確認
    assert all(0 <= r <= 0xFFFFFFFF for r in results)

    # 連続する値での分散確認（ハッシュの基本的な性質）
    assert len(set(results)) > 99  # 大部分が異なる値になることを期待


def test_wang_hash32() -> None:
    """wang_hash32のテスト。"""
    results = [pytilpack.random.wang_hash32(i) for i in range(100)]

    # 固定値のテスト
    assert results[0] == 3221834090
    assert results[1] == 656419997
    assert pytilpack.random.wang_hash32(0xFFFFFFFF) == 1368758739

    # 同じ入力には同じ出力
    results2 = [pytilpack.random.wang_hash32(i) for i in range(len(results))]
    assert results == results2

    # 出力が32ビット範囲であることの確認
    assert all(0 <= r <= 0xFFFFFFFF for r in results)

    # 連続する値での分散確認（ハッシュの基本的な性質）
    assert len(set(results)) > 99  # 大部分が異なる値になることを期待
