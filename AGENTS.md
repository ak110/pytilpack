# AGENTS.md: pytilpack

## 概要

主要Pythonライブラリ向けの軽量ユーティリティ集。
モジュール単位の個別importとextras単位の依存管理を採用し、利用者は必要なモジュールだけ取り込む。

## 開発手順

コミット前の検証方法: `make test`（特定ファイルに限定する場合は`uvx --exclude-newer-package pyfltr=false pyfltr run <path>`）

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
