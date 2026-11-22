import pytilpack.random


def test_xor_shift32() -> None:
    results = [pytilpack.random.xor_shift32(i) for i in range(100)]

    assert results[0] == 0
    assert results[1] == 270369
    assert pytilpack.random.xor_shift32(0xFFFFFFFF) == 253983

    results2 = [pytilpack.random.xor_shift32(i) for i in range(len(results))]
    assert results == results2

    assert all(0 <= r <= 0xFFFFFFFF for r in results)

    assert len(set(results)) > 99


def test_wang_hash32() -> None:
    results = [pytilpack.random.wang_hash32(i) for i in range(100)]

    assert results[0] == 3221834090
    assert results[1] == 656419997
    assert pytilpack.random.wang_hash32(0xFFFFFFFF) == 1368758739

    results2 = [pytilpack.random.wang_hash32(i) for i in range(len(results))]
    assert results == results2

    assert all(0 <= r <= 0xFFFFFFFF for r in results)

    assert len(set(results)) > 99
