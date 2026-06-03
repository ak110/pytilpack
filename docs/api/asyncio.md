# pytilpack.asyncio

!!! note "pytilpack.asyncio.run の制約"
    親イベントループが実行中の状態から `pytilpack.asyncio.run` を呼ぶ場合、
    `coro` は別スレッドの新規ループで実行される。
    別ループの破棄は親ループへ波及しないため、呼び出し後も親ループの処理は継続できる。

    `coro` 内から親ループ起源のリソース（SQLAlchemy `AsyncEngine` ・ `asyncio.Queue` ・
    `asyncio.Event` ・ `asyncio.Task` ・親ループに紐付く `asyncio.Future` など）を参照しない。
    別ループからのアクセスとなり「different loop」例外や
    `Future ... attached to a different loop` 等の事象が発生する。
    `coro` は独立した非同期処理として完結する形で渡す。

::: pytilpack.asyncio
    options:
      show_submodules: true
