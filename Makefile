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

fix:
	uv run ruff check --fix --unsafe-fixes

format:
	SKIP=pyfltr $(UV_RUN) pre-commit run --all-files
	-$(UV_RUN) pyfltr --exit-zero-even-if-formatted --commands=fast

test:
	SKIP=pyfltr $(UV_RUN) pre-commit run --all-files
	$(UV_RUN) pyfltr --exit-zero-even-if-formatted

docs:
	$(UV_RUN) mkdocs serve

.PHONY: help update update-actions test format docs
