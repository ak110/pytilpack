# サプライチェーン攻撃対策としてlockfileを常に尊重する。依存を更新する場合のみ
# `env --unset=UV_FROZEN` で一時的に無効化する（`UV_FROZEN=` の空文字代入はuvがエラー扱い）。
export UV_FROZEN := 1

help:
	@cat Makefile

# 開発環境のセットアップ
# --config明示指定はprekのworkspace再帰探索（サブディレクトリの.pre-commit-config.yamlも
# 実行対象へ含める仕様）を無効化するため（prek 0.4.11で確認）。
setup:
	uv sync --all-groups --all-extras
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
	@command -v mise >/dev/null 2>&1 || { echo "mise未検出、スキップ"; exit 0; }; \
	GITHUB_TOKEN=$$(gh auth token) mise exec -- pinact run --update --min-age=1

# フォーマット + 軽量lint（開発時の手動実行用。自動修正あり）
format:
	uvx pyfltr fast

# 全チェック実行（これを通過すればコミット可能）
test:
	uvx pyfltr run

docs:
	uv run mkdocs serve

.PHONY: help setup update update-actions format test docs
