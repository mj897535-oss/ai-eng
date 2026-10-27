# SyntaxLens Monorepo Makefile
# Cross-platform development targets

PYTHON := python
ifeq ($(OS),Windows_NT)
    VENV_PYTHON := .venv\Scripts\python
    VENV_PYTEST := .venv\Scripts\pytest
    VENV_RUFF := .venv\Scripts\ruff
    VENV_MYPY := .venv\Scripts\mypy
    VENV_ALEMBIC := .venv\Scripts\alembic
else
    VENV_PYTHON := .venv/bin/python
    VENV_PYTEST := .venv/bin/pytest
    VENV_RUFF := .venv/bin/ruff
    VENV_MYPY := .venv/bin/mypy
    VENV_ALEMBIC := .venv/bin/alembic
endif

.PHONY: help setup dev test lint typecheck e2e migrate seed clean openapi

help:
	@echo "SyntaxLens Monorepo Targets:"
	@echo "  make setup      - Install dependencies for backend and frontend"
	@echo "  make dev        - Start local development services via Docker Compose"
	@echo "  make test       - Run backend tests (immutability, metrics, API)"
	@echo "  make lint       - Run Ruff on API and ESLint on Web"
	@echo "  make typecheck  - Run Mypy strict on API and TSC on Web"
	@echo "  make e2e        - Run Playwright end-to-end tests"
	@echo "  make migrate    - Run Alembic database migrations"
	@echo "  make seed       - Seed initial research rubrics, task bank, and accounts"
	@echo "  make openapi    - Generate OpenAPI schema and TypeScript definitions"

setup:
	$(PYTHON) -m venv .venv
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -r apps/api/requirements.txt
	npm --prefix apps/web install
	@if not exist .env (copy .env.example .env) || test -f .env || cp .env.example .env

dev:
	docker compose up --build

test:
	$(VENV_PYTEST) apps/api/tests -v

lint:
	$(VENV_RUFF) check apps/api
	npm --prefix apps/web run lint

typecheck:
	$(VENV_MYPY) --config-file apps/api/pyproject.toml apps/api/app
	npm --prefix apps/web run typecheck

e2e:
	npx playwright test

migrate:
	cd apps/api && $(VENV_ALEMBIC) upgrade head

seed:
	$(VENV_PYTHON) scripts/seed.py

openapi:
	$(VENV_PYTHON) scripts/generate_openapi.py

clean:
	rm -rf .pytest_cache apps/api/.ruff_cache apps/api/.mypy_cache apps/web/.next
