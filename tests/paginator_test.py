"""pytilpack.paginatorのテストコード。"""

import pytest

import pytilpack.paginator


def test_paginator_basic() -> None:
    """Paginator基本動作の確認。"""
    paginator = pytilpack.paginator.Paginator(page=1, per_page=3, items=[1, 2, 3], total=10)
    assert paginator.page == 1
    assert paginator.per_page == 3
    assert paginator.total_items == 10
    assert paginator.pages == 4
    assert paginator.has_prev is False
    assert paginator.has_next is True


def test_paginator_invalid_page() -> None:
    """無効なpageでValueErrorが送出されることを確認。

    assert文からValueErrorに変更したため、`-O`実行時も検証が効くようになる。
    """
    with pytest.raises(ValueError, match="page"):
        pytilpack.paginator.Paginator(page=0, per_page=3, items=[], total=0)

    with pytest.raises(ValueError, match="page"):
        pytilpack.paginator.Paginator(page=-1, per_page=3, items=[], total=0)


def test_paginator_invalid_per_page() -> None:
    """無効なper_pageでValueErrorが送出されることを確認。"""
    with pytest.raises(ValueError, match="per_page"):
        pytilpack.paginator.Paginator(page=1, per_page=0, items=[], total=0)

    with pytest.raises(ValueError, match="per_page"):
        pytilpack.paginator.Paginator(page=1, per_page=-1, items=[], total=0)


def test_paginator_invalid_total() -> None:
    """無効なtotalでValueErrorが送出されることを確認。"""
    with pytest.raises(ValueError, match="total"):
        pytilpack.paginator.Paginator(page=1, per_page=3, items=[], total=-1)
