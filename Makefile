UV_RUN := uv run --frozen --all-extras --all-groups

help:
	@cat Makefile

update:
	uv sync --upgrade --all-extras --all-groups
	uv run pre-commit autoupdate
	$(MAKE) test

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

.PHONY: help update test format docs
