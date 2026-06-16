# Developer entry points — mirror CI (.github/workflows/ci.yml) and docker/ci.sh.
# Assumes an activated virtualenv (see CONTRIBUTING.md). Run `make help` for targets.

export PYTHONPATH := src
export DJANGO_SETTINGS_MODULE := config.settings_test

COV_ARGS := --cov=warehouse --cov=config --cov=sec_edgar --cov=public_data --cov=api \
	--cov-report=term-missing --cov-fail-under=50

.PHONY: help install lint format typecheck test migrations check audit precommit all

help:  ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## Install runtime + dev dependencies
	pip install -r requirements.txt -r requirements-dev.txt

lint:  ## Ruff lint (matches CI lint job)
	ruff check src tests

format:  ## Ruff auto-format
	ruff format src tests

typecheck:  ## Mypy (advisory; matches CI typecheck job)
	mypy src

test:  ## Pytest with coverage gate (matches docker/ci.sh)
	pytest -q $(COV_ARGS)

migrations:  ## Fail if model changes lack migrations (matches CI)
	python src/manage.py makemigrations --check --dry-run

check:  ## Django system check
	python src/manage.py check

audit:  ## Dependency vulnerability scan (advisory)
	pip-audit || true

precommit:  ## Run all pre-commit hooks on the repo
	pre-commit run --all-files

all: lint migrations test  ## Run the blocking CI checks (lint + migrations + tests)

ci: lint migrations test typecheck audit  ## Everything, incl. advisory typecheck + audit
