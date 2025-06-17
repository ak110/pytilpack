help:
	@cat Makefile

update:
	uv sync --upgrade --all-extras --all-groups
	uv run pre-commit autoupdate
	$(MAKE) test

format:
	uv run pyfltr --exit-zero-even-if-formatted --commands=fast

test:
	uv run pyfltr --exit-zero-even-if-formatted

.PHONY: help update test format
