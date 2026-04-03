UV_RUN := uv run --frozen --all-extras --all-groups

help:
	@cat Makefile

update:
	uv sync --upgrade --all-extras --all-groups
	uv run pre-commit autoupdate
	$(MAKE) update-actions
	$(MAKE) test

# GitHub Actionsのアクションをハッシュピンで最新化（mise未導入時はスキップ）
update-actions:
	@command -v mise >/dev/null 2>&1 || { echo "mise未検出、スキップ"; exit 0; }; \
	GITHUB_TOKEN=$$(gh auth token) mise exec -- pinact run --update --min-age 1

# フォーマット + 軽量lint（開発時の手動実行用。自動修正あり）
format:
	$(UV_RUN) ruff check --fix --unsafe-fixes
	SKIP=pyfltr $(UV_RUN) pre-commit run --all-files
	-$(UV_RUN) pyfltr --exit-zero-even-if-formatted --commands=fast

# 全チェック実行（これが通ればコミットしてOK）
test:
	$(UV_RUN) ruff check --fix --unsafe-fixes
	SKIP=pyfltr $(UV_RUN) pre-commit run --all-files
	$(UV_RUN) pyfltr --exit-zero-even-if-formatted

docs:
	$(UV_RUN) mkdocs serve

.PHONY: help update update-actions format test docs
