---
name: add-module
description: pytilpackの公開モジュールまたはサブパッケージを新しく追加するときに使う。
---

# pytilpackのモジュール追加

本スキルはモジュールの実装と依存・テスト・文書の追加を完了させる手順を提供する。
実行主体は着手時に`AGENTS.md`を読み、次の資料を全文読む。

- `docs/development/architecture.md`: 依存、公開API、テストと文書の規約
- `docs/development/development.md`: 「モジュールの追加・変更」の作業手順と検証
- `docs/guide/index.md`: 現在のextras対応表と8分類のモジュール一覧

## 実施

1. モジュールの責務と公開名を決め、architectureの依存規約に照らして実装する。
2. developmentの「モジュールの追加・変更」に従い、依存宣言、`EXTRA_MODULES`、API文書、利用ガイドとMkDocsの分類、テストを更新する。
3. 同節のコマンドで実装と文書を検証し、失敗を是正する。依存の最小性、任意依存の関数内import、公開APIとテストの対応は実装を読んで確かめる。

CLIは`pytilpack/cli/main.py:_SUBCOMMANDS`と`docs/guide/cli.md`で扱う。
私的モジュールは公開API一覧へ追加せず、公開関数の利用側のテストで検証する。
完了時は変更したモジュール、依存、文書と検証結果を呼出元へ返す。
