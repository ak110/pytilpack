help:
	@cat Makefile

update:
	uv sync --upgrade --all-extras --all-groups
	uv run pre-commit autoupdate
	$(MAKE) test

format:
	uv run ruff format
	uv run ruff check --fix

test:
	uv run pre-commit run --all-files
	uv run mypy pytilpack
	uv run pytest

.PHONY: help update test format
