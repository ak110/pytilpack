import pytest

import pytilpack.paginator


def test_paginator_basic() -> None:
    paginator = pytilpack.paginator.Paginator(page=1, per_page=3, items=[1, 2, 3], total=10)
    assert paginator.page == 1
    assert paginator.per_page == 3
    assert paginator.total_items == 10
    assert paginator.pages == 4
    assert paginator.has_prev is False
    assert paginator.has_next is True


def test_paginator_invalid_page() -> None:
    with pytest.raises(ValueError, match="page"):
        pytilpack.paginator.Paginator(page=0, per_page=3, items=[], total=0)

    with pytest.raises(ValueError, match="page"):
        pytilpack.paginator.Paginator(page=-1, per_page=3, items=[], total=0)


def test_paginator_invalid_per_page() -> None:
    with pytest.raises(ValueError, match="per_page"):
        pytilpack.paginator.Paginator(page=1, per_page=0, items=[], total=0)

    with pytest.raises(ValueError, match="per_page"):
        pytilpack.paginator.Paginator(page=1, per_page=-1, items=[], total=0)


def test_paginator_invalid_total() -> None:
    with pytest.raises(ValueError, match="total"):
        pytilpack.paginator.Paginator(page=1, per_page=3, items=[], total=-1)


def test_paginator_no_page_messages() -> None:
    paginator = pytilpack.paginator.Paginator[int](page=1, per_page=10, items=[], total=0)
    with pytest.raises(ValueError, match="Check has_next before calling next\\(\\)"):
        paginator.next()
    with pytest.raises(ValueError, match="Check has_prev before calling prev\\(\\)"):
        paginator.prev()
