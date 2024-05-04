
help:
	@cat Makefile

update:
	poetry update
	$(MAKE) test

test:
	poetry install --no-interaction --extras=all
	poetry run pyfltr --exit-zero-even-if-formatted

format:
	poetry run pyfltr --exit-zero-even-if-unformatted --commands=fast

.PHONY: help update test format
