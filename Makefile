VENV := .venv

PYTHON := poetry run python
TOUCH := $(PYTHON) -c 'import sys; from pathlib import Path; Path(sys.argv[1]).touch()'

# Find all the .po we want to format into .mo files.
PO_FILES := $(shell find permaculture/locales -name '*.po')
MO_FILES := $(PO_FILES:.po=.mo)

poetry.lock: pyproject.toml
	poetry lock

# Build venv with both conda and python deps.
$(VENV): environment.yml
	@echo Installing Conda environment
	@conda env update --prefix $@ --prune --file $^
	@echo Installing Poetry environment
	@poetry install
	@$(TOUCH) $@

# Convenience target to build venv.
.PHONY: setup
setup: $(VENV)

.PHONY: check
check: $(VENV)
	@echo Checking Poetry lock: Running poetry lock --check
	@poetry lock --check
	@echo Linting code: Running pre-commit
	@poetry run pre-commit run -a

%.po: $(VENV)

%.mo: %.po
	@poetry run scripts/msgfmt.py --output-file $@ $^

# Convenience target to build locales.
.PHONY: locales
locales: $(MO_FILES)

.PHONY: test
test: locales
	@echo Testing code: Running pytest
	@poetry run coverage run -p -m pytest

.PHONY: coverage
coverage: $(VENV)
	@echo Testing covarage: Running coverage
	@poetry run coverage combine
	@poetry run coverage html --skip-covered --skip-empty
	@poetry run coverage report

.PHONY: docs
docs: $(VENV)
	@echo Building docs: Running sphinx-build
	@poetry run sphinx-build -W -d build/doctrees docs build/html

.PHONY: build
build: locales
	@echo Creating wheel file
	@poetry build

.PHONY: publish
publish:
	@echo Publishing: Dry run
	@poetry config repositories.test-pypi https://test.pypi.org/legacy/
	@poetry config pypi-token.test-pypi $(PYPI_TOKEN)
	@poetry publish --repository test-pypi --dry-run
	@echo Publishing
	@poetry publish --repository test-pypi

.PHONY: clean
clean:
	@echo Cleaning ignored files
	@git clean -Xfd

.DEFAULT_GOAL := test
