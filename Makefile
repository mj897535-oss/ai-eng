# SyntaxLens Makefile
# Cross-platform development targets

PYTHON := python
VENV_BIN := .venv/Scripts
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

.PHONY: help setup dev test lint typecheck e2e migrate seed clean

help:
	@echo "SyntaxLens Development Targets:"
	@echo "  make setup      - Initialize virtualenv, install dependencies, prepare .env"
	@echo "  make dev        - Start local development services via Docker Compose"
	@echo "  make test       - Run backend and pure research calculation test suites"
	@echo "  make lint       - Run ruff linter on backend and ESLint on frontend"
	@echo "  make typecheck  - Run mypy strict type checker and TypeScript compiler"
	@echo "  make e2e        - Run Playwright end-to-end tests"
	@echo "  make migrate    - Run Alembic database migrations"
	@echo "  make seed       - Seed initial research rubrics, task bank, and pilot accounts"

setup:
	$(PYTHON) -m venv .venv
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -r backend/requirements.txt
	@if not exist .env (copy .env.example .env) || test -f .env || cp .env.example .env

dev:
	docker compose up --build

test:
	$(VENV_PYTEST) backend/tests -v

lint:
	$(VENV_RUFF) check backend

typecheck:
	$(VENV_MYPY) --strict backend/app

e2e:
	npx playwright test

migrate:
	cd backend && $(VENV_ALEMBIC) upgrade head

seed:
	$(VENV_PYTHON) scripts/seed.py

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache __pycache__
