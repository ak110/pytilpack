# pytilpack.python

`SingletonMixin.get_singleton()`は初期化が成功したインスタンスだけを返す。
初期化に失敗した場合は次の取得で初期化をやり直す。
初期化から別クラスのsingletonを取得でき、同じクラスへの再帰取得は`RuntimeError`になる。

::: pytilpack.python
