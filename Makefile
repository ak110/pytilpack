# サプライチェーン攻撃対策としてlockfileを常に尊重する。依存を更新する場合のみ
# `env --unset UV_FROZEN` で一時的に無効化する（`UV_FROZEN=` の空文字代入はuvがエラー扱い）。
export UV_FROZEN := 1

help:
	@cat Makefile

# 開発環境セットアップ
setup:
	env --unset UV_FROZEN uv sync --all-extras --all-groups
	uv run pre-commit install

# 依存パッケージをアップグレードし全テスト実行
update:
	env --unset UV_FROZEN uv sync --upgrade --all-extras --all-groups
	uv run pre-commit autoupdate
	$(MAKE) update-actions
	$(MAKE) test

# GitHub Actionsのアクションをハッシュピンで最新化（mise未導入時はスキップ）
update-actions:
	@command -v mise >/dev/null 2>&1 || { echo "mise未検出、スキップ"; exit 0; }; \
	GITHUB_TOKEN=$$(gh auth token) mise exec -- pinact run --update --min-age 1

# フォーマット + 軽量lint（開発時の手動実行用。自動修正あり）
format:
	SKIP=pyfltr uv run pre-commit run --all-files
	-uv run pyfltr fix
	-uv run pyfltr fast

# 全チェック実行（これが通ればコミットしてOK）
test:
	SKIP=pyfltr uv run pre-commit run --all-files
	uv run pyfltr run

docs:
	uv run mkdocs serve

.PHONY: help setup update update-actions format test docs
