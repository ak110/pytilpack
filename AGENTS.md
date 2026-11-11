# AGENTS.md: pytilpack

## 概要

主要Pythonライブラリ向けの軽量ユーティリティ集。
モジュール単位の個別importとextras単位の依存管理を採用し、利用者は必要なモジュールだけ取り込む。

## 共通品質基準

設計・コード・テスト・文書の作成と修正では`agent-basics:writing-standards`を起動し、変更対象に該当するreferencesを読む。
レビューと指摘の採否判断では`agent-basics:review-standards`を起動する。
導入方法は[開発ガイド](docs/development/development.md)を参照する。本書の固有規約も併用する。

## 開発手順

- 手元の検証は、変更したファイルと参照をたどって特定した利用側のテスト・lintを対象に指定した
  `uvx --exclude-newer-package pyfltr=false pyfltr run <path>`で行う。
  対象を渡さない全体の実行（`make test`、対象なしの`pyfltr run`）は求めず、全体のlintとテストはpush後のCIの結果で判定する
  - 共通設定・`conftest.py`・依存の版指定とlockファイルなど利用側を列挙しきれない変更でも、全体の実行へ広げない。
    列挙できた範囲だけを実行し、残りはCIの結果で判定する
  - commit時のフック（`pyfltr fast`）は従来どおり動く。手元で全体を確かめたい場合は`make test`を使ってよい

## アーキテクチャの参照先

[docs/development/architecture.md](docs/development/architecture.md)は依存・公開API・テスト・文書の規約を定める。
モジュールや依存を変更するときは該当章を参照する。利用者向けの対応表は[利用者向けガイド](docs/guide/index.md)にある。

## 実装上の不変条件・コーディング規約

- コア依存は最小限に保ち、任意の依存はextrasへ宣言する。定義元と依存方向はarchitectureの「モジュールの構成と依存」に従う
- コア依存に原則上限を設けない。非互換などを実機・公式資料で確認した例外だけに上限と解除条件を残す。詳細は同章に従う
- importは原則トップレベルに置く。任意extraやUnix専用依存の関数内importは同章と「公開API設計方針」の条件に従う
- 厳密なファイル権限は`os.open`などで作成時に確定する。architectureの「公開API設計方針」に従う
- SQLAlchemyの同じサブクラスはsession fixtureで1回だけ初期化し、各テスト前に全行を削除して自分の挿入行だけを検証する。architectureの「テスト規約」の厳守規定に従う

## 注意点

- モジュール追加時は`add-module`スキルを使用する
- モジュール・extras・CLI・API文書の対応を変更したときは`check-module-sync`スキルを使用する
