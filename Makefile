VENV := .venv

RUN := uv run
PYTHON := $(RUN) python
TOUCH := $(PYTHON) -c 'import sys; from pathlib import Path; Path(sys.argv[1]).touch()'

# Find all the .po we want to format into .mo files.
PO_FILES := $(shell find permaculture/locales -name '*.po')
MO_FILES := $(PO_FILES:.po=.mo)

uv.lock: pyproject.toml
	uv lock

# Build .venv with deps.
$(VENV): uv.lock
	@echo "==> Installing environment..."
	@uv sync --frozen --all-extras
	@$(TOUCH) $@

# Convenience target to build venv.
.PHONY: setup
setup: $(VENV)

.PHONY: check
check: $(VENV)
	@echo "==> Checking uv lock..."
	@uv lock --check
	@echo "==> Linting Python code..."
	@$(RUN) ruff check .

%.po: $(VENV)

%.mo: %.po
	@$(RUN) scripts/msgfmt.py --output-file $@ $^

# Convenience target to build locales.
.PHONY: locales
locales: $(MO_FILES)

.PHONY: test
test: locales
	@echo "==> Testing Python code..."
	@$(RUN) coverage run -p -m pytest

.PHONY: coverage
coverage: $(VENV)
	@echo "==> Checking coverage..."
	@$(RUN) coverage combine
	@$(RUN) coverage html --skip-covered --skip-empty
	@$(RUN) coverage report

.PHONY: docs
docs: $(VENV)
	@echo "==> Building docs..."
	@$(RUN) sphinx-build -W -d build/doctrees docs build/html

.PHONY: build
build: locales
	@echo "==> Creating wheel..."
	@$(PYTHON) -m build

.PHONY: publish
publish:
	@echo "==> Publishing: Dry run..."
	@TWINE_USERNAME=__token__ TWINE_PASSWORD=$(PYPI_TOKEN) \
	  $(PYTHON) -m twine upload --repository-url https://test.pypi.org/legacy/ --dry-run dist/*
	@echo "==> Publishing..."
	@TWINE_USERNAME=__token__ TWINE_PASSWORD=$(PYPI_TOKEN) \
	  $(PYTHON) -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*

.PHONY: clean
clean:
	@echo "==> Cleaning ignored files..."
	@git clean -Xfd

.DEFAULT_GOAL := test
