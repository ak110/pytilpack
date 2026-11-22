__lazy_modules__ = ["typing"]

import typing


class Paginator[T]:
    def __init__(self, page: int, per_page: int, items: list[T], total: int):
        if page < 1:
            raise ValueError(f"pageは1以上でなければなりません: page={page}")
        if per_page < 1:
            raise ValueError(f"per_pageは1以上でなければなりません: per_page={per_page}")
        if total < 0:
            raise ValueError(f"totalは0以上でなければなりません: total={total}")
        self.page = page
        self.per_page = per_page
        self.items = items
        self.total_items = total

    @property
    def pages(self) -> int:
        if self.total_items <= 0:
            return 1
        return (self.total_items + self.per_page - 1) // self.per_page

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def prev_num(self) -> int:
        return self.page - 1

    @property
    def next_num(self) -> int:
        return self.page + 1

    def next(self) -> typing.Self:
        if not self.has_next:
            raise ValueError("No next page. Check has_next before calling next().")
        return self.__class__(
            page=self.next_num,
            per_page=self.per_page,
            items=self.items,
            total=self.total_items,
        )

    def prev(self) -> typing.Self:
        if not self.has_prev:
            raise ValueError("No previous page. Check has_prev before calling prev().")
        return self.__class__(
            page=self.prev_num,
            per_page=self.per_page,
            items=self.items,
            total=self.total_items,
        )

    def iter_pages(
        self,
        left_edge: int = 2,
        left_current: int = 2,
        right_current: int = 4,
        right_edge: int = 2,
    ) -> list[int | None]:
        last = 0
        result: list[int | None] = []
        for num in range(1, self.pages + 1):
            if (
                num <= left_edge
                or (self.page - left_current <= num <= self.page + right_current)
                or num > self.pages - right_edge
            ):
                if last + 1 != num:
                    result.append(None)
                result.append(num)
                last = num
        return result
