# Eco.AI Assembly — developer workflow targets.
# `make setup` → venv + deps + .env;  `make index` → marketplace cache + RAG index;
# `make preflight` → validate the stack;  `make up` → docker compose.

PYTHON ?= python3

.PHONY: setup index preflight up test help

help:
	@echo "Targets:"
	@echo "  setup      - create .venv, install agent/requirements.txt, seed .env from env.example"
	@echo "  index      - fetch marketplace components and build the RAG index (needs ECO_API_TOKEN / OPENAI_API_KEY)"
	@echo "  preflight  - validate binaries, cache, index before starting"
	@echo "  up         - docker compose up --build"

setup:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r agent/requirements.txt
	@test -f .env || (cp env.example .env && echo "[setup] seeded .env from env.example")

index:
	.venv/bin/python scripts/fetch_marketplace.py
	.venv/bin/python scripts/build_marketplace_index.py

preflight:
	.venv/bin/python scripts/dev_preflight.py --fix

up:
	docker compose up --build

test:
	.venv/bin/python -m pytest agent/internal/tests
	.venv/bin/python -m compileall -q agent backend eco_harness scripts
