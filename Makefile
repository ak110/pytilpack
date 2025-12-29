help:
	@cat Makefile

update:
	uv sync --upgrade --all-extras --all-groups
	uv run pre-commit autoupdate
	$(MAKE) test

fix:
	uv run ruff check --fix --unsafe-fixes

format:
	uv sync --frozen --all-extras --all-groups
	SKIP=pyfltr uv run pre-commit run --all-files
	-uv run pyfltr --exit-zero-even-if-formatted --commands=fast

test:
	uv sync --frozen --all-extras --all-groups
	SKIP=pyfltr uv run pre-commit run --all-files
	uv run pyfltr --exit-zero-even-if-formatted

.PHONY: help update test format
