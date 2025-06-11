help:
	@cat Makefile

update:
	uv sync --upgrade --all-extras --all-groups
	$(MAKE) test

test:
	uv run pyfltr --exit-zero-even-if-formatted

format:
	uv run pyfltr --exit-zero-even-if-formatted --commands=fast

.PHONY: help update test format
