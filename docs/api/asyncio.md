# pytilpack.asyncio

## ジョブの状態と通知

`JobRunner`は`Job.run()`の直前に`status`を`running`へ変更し、実行結果を確定してから通知メソッドを呼ぶ。
`on_finished`・`on_canceled`・`on_errored`を上書きする場合も、状態設定のために`super()`を呼ぶ必要はない。
通知メソッドの例外は警告ログに記録され、本体の実行結果は保持される。

### 通知メソッドの変更履歴

通知メソッドを直接呼んでも`status`は変化しなくなった。
ジョブは`JobRunner`を通じて実行し、通知メソッドには追加の終了処理を実装する。

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
