# サプライチェーン攻撃対策としてlockfileを常に尊重する。依存を更新する場合のみ
# `env --unset=UV_FROZEN` で一時的に無効化する（`UV_FROZEN=` の空文字代入はuvがエラー扱い）。
export UV_FROZEN := 1

help:
	@cat Makefile

# 仮想環境を、ロックファイルが選ぶ全依存グループ・extrasと`.python-version`の基準Python版へそろえる。
# pyfltrのPython系ツールは`uv run --frozen`でこの仮想環境から起動するため、検査の前に同期する。
# `uv sync`は余分なパッケージを除き、`--python`は`UV_PYTHON`などで別の版が指定された環境でも
# 基準の版で仮想環境を再作成する。`uv run`の自動同期は余分なパッケージを残すため、この同期に代えない（uv 0.13.1で確認）。
sync:
	uv sync --all-groups --all-extras --python "$$(cat .python-version)"

# 開発環境のセットアップ
# --config明示指定はprekのworkspace再帰探索（サブディレクトリの.pre-commit-config.yamlも
# 実行対象へ含める仕様）を無効化するため（prek 0.4.11で確認）。
setup: sync
	uvx prek --config=.pre-commit-config.yaml install
	git config --local commit.template .gitmessage

# 依存パッケージをアップグレードし全テスト実行
update:
	env --unset=UV_FROZEN uv sync --upgrade --all-groups --all-extras
	uvx prek --config=.pre-commit-config.yaml autoupdate
	$(MAKE) update-actions
	$(MAKE) test

# GitHub Actionsのアクションをハッシュピンで最新化（mise未導入時はスキップ）
update-actions:
	@command -v mise >/dev/null 2>&1 || { echo "mise未検出のためGitHub Actionsのピン更新をスキップした（他の更新は続行する）。ピンも更新する場合はmiseを導入して make update-actions を再実行する"; exit 0; }; \
	GITHUB_TOKEN=$$(gh auth token) mise exec -- pinact run --update --min-age=1

# pyfltrの呼び出しは推奨ガイドから意図して外れ、公開待機の例外を指定する。
# グローバルuv設定のexclude-newerは公開直後のpyfltrを除外するが、uvxはpyproject.tomlの[tool.uv]を読まないため、
# コマンドラインでpyfltrだけを例外にして公開直後の版を使う。
# 推奨ガイドの例に加えて`UV_PYTHON`を外す。pyfltrがPython系ツールを起動する`uv run`は`UV_PYTHON`を読み、
# 別の版が指定されていると同期済みの仮想環境をその版で再作成するため（uv 0.13.1で確認）。
# 外すと`uv run`は`.python-version`の基準版を選び、`sync`がそろえた仮想環境をそのまま使う。

# フォーマット + 軽量lint（開発時の手動実行用。自動修正あり）
format: sync
	env --unset=UV_PYTHON uvx --exclude-newer-package pyfltr=false pyfltr fast

# 全チェック実行（これを通過すればコミット可能）
test: sync
	env --unset=UV_PYTHON uvx --exclude-newer-package pyfltr=false pyfltr run

docs:
	uv run mkdocs serve

.PHONY: help sync setup update update-actions format test docs
