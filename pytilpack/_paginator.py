"""ページネーション用ユーティリティ。"""

import typing

T = typing.TypeVar("T")


class Paginator[T]:
    """ページング用簡易ヘルパ

    Args:
        page: 1オリジンのページ番号
        per_page: 1ページあたりのアイテム数
        items: 現在のページのデータ
        total: 全データ件数

    例::

        {% macro render_pagination(endpoint, paginator, **kwargs) %}
        <nav>
            <ul class="pagination justify-content-center">
                <li class="page-item{% if not paginator.has_prev %} disabled{% endif %}">
                    <a class="page-link" href="{{ url_for(endpoint, page=paginator.prev_num, **kwargs) }}">&lt;</a>
                </li>
                {% for page in paginator.iter_pages() %}
                    {% if page is none %}
                        <li class="page-item disabled">...</li>
                    {% else %}
                        <li class="page-item{% if paginator.page == page %} active{% endif %}">
                            <a class="page-link" href="{{ url_for(endpoint, page=page, **kwargs) }}">{{ page }}</a>
                        </li>
                    {% endif %}
                {% endfor %}
                <li class="page-item{% if not paginator.has_next %} disabled{% endif %}">
                    <a class="page-link" href="{{ url_for(endpoint, page=paginator.next_num, **kwargs) }}">&gt;</a>
                </li>
            </ul>
        </nav>
        {% endmacro %}

    参考:
        - <https://flask-sqlalchemy.readthedocs.io/en/stable/api/#flask_sqlalchemy.pagination.Pagination>

    """

    def __init__(self, page: int, per_page: int, items: list[T], total: int):
        assert page >= 1
        assert per_page >= 1
        assert total >= 0
        self.page = page
        self.per_page = per_page
        self.items = items
        self.total_items = total

    @property
    def pages(self) -> int:
        """ページ数。"""
        if self.total_items <= 0:
            return 1
        return (self.total_items + self.per_page - 1) // self.per_page

    @property
    def has_prev(self) -> bool:
        """前ページがあるか否か。"""
        return self.page > 1

    @property
    def has_next(self) -> bool:
        """次ページがあるか否か。"""
        return self.page < self.pages

    @property
    def prev_num(self) -> int:
        """前ページ"""
        return self.page - 1

    @property
    def next_num(self) -> int:
        """次ページ"""
        return self.page + 1

    def next(self) -> typing.Self:
        """次ページのPaginatorオブジェクト。"""
        if not self.has_next:
            raise ValueError("No next page")
        return self.__class__(
            page=self.next_num,
            per_page=self.per_page,
            items=self.items,
            total=self.total_items,
        )

    def prev(self) -> typing.Self:
        """前ページのPaginatorオブジェクト。"""
        if not self.has_prev:
            raise ValueError("No previous page")
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
        """ページネーションウィジェット用のページ番号を生成します。
        ページの先頭と末尾の間にあるスキップされたページは None で表現されます。

        例えば、総ページ数が 20 ページで、現在のページが 7 ページの場合、以下の値が生成されます。

        1, 2, None, 5, 6, 7, 8, 9, 10, 11, None, 19, 20

        Args:
            left_edge: 最初のページから表示するページ数。
            left_current: 現在のページの左側に表示されるページ数。
            right_current: 現在のページの右側に表示されるページ数。
            right_edge: 最後のページから表示するページ数。

        Returns:
            ページ番号のリスト。ページ番号が連続していない場合はNoneを挟む。
        """
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
