---
verified-digest: f5c8787571cbfbb9997f25358323e9ded94832456b2e20cb6e2937167c5fe605
name: sync-link-boundary
description: pathlib.syncとsync CLIのリンク処理、削除、ルートの重なりを変えたときに、コピー先の境界を網羅検査する。
verifies:
  - pytilpack/pathlib.py
  - pytilpack/cli/sync.py
  - tests/pathlib_sync_links_test.py
---

# 同期のリンク境界

同期後も解決済みのコピー先ルートの外にある既存項目の種類、内容、モード、リンク先は変わらない。外に新規作成できるのはコピー先の祖先ディレクトリだけである。この境界が破れると、同期対象に指定していないデータを失いうる。

`tests/pathlib_sync_links_test.py`は`pytilpack.pathlib.sync`と同期CLIのサブコマンドを各ケースで1回呼び、一時ディレクトリの前後の状態を比較する。同一ルートでは変更しないこと、重なった別ルートでは変更せずに拒否することも確かめる。

ディレクトリのケースでは、ルートの関係4種、コピー先の有無、削除の有無、項目の深さ2段、コピー元の項目7種、コピー先の項目9種から、成立する組をAPIとCLIで列挙する。ファイルのコピー元と、コピー先ルートそのものがリンクの場合は個別ケースで扱う。並行した外部更新、コピー元の循環リンク、Windowsジャンクションの実作成は範囲外である。シンボリックリンクを作れない環境ではリンクを使うケースは実行しない。

## 実行と更新

```bash
uvx --exclude-newer-package pyfltr=false pyfltr run tests/pathlib_sync_links_test.py
```

感度確認では実ファイルを操作せず、コピー先外の差分を調べる判定器に変更あり・なしの前後データを渡す。失敗した場合は、表示された入力の組と前後の差を契約に照らし、実装と期待値のどちらが違うか確かめる。失敗に合わせて性質を弱めない。

対象コードの変更後は、実装と期待値の対応を確認して再実行する。対象のケースがスキップされずに成功してから、追従記録を更新する。

```bash
uvx --exclude-newer-package pyfltr=false pyfltr verification-sync --update .claude/skills/sync-link-boundary/SKILL.md
```
