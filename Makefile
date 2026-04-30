.DEFAULT_GOAL := help
.PHONY: help install install-dev env seed run reset clean front-install front test

BACKEND  := backend
FRONTEND := frontend
VENV     := $(BACKEND)/.venv
PY       := $(VENV)/bin/python
PIP      := $(VENV)/bin/pip
UVICORN  := $(VENV)/bin/uvicorn

help:
	@echo "Foyre — local dev"
	@echo
	@echo "  Backend"
	@echo "    make install        Create venv and install backend dependencies"
	@echo "    make env            Copy backend/.env.example -> backend/.env (once)"
	@echo "    make seed           Create DB and the initial admin user"
	@echo "    make run            Run the API on http://0.0.0.0:8000"
	@echo "    make reset          Delete the local SQLite DB"
	@echo "    make clean          Remove venv and local DB"
	@echo "    make test           Run backend unit tests (pytest)"
	@echo "  Frontend"
	@echo "    make front-install  Install frontend dependencies"
	@echo "    make front          Run the Vite dev server on http://0.0.0.0:5173"

install: $(VENV)/bin/activate

$(VENV)/bin/activate: $(BACKEND)/requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install -q --upgrade pip
	$(PIP) install -q -r $(BACKEND)/requirements.txt
	@touch $(VENV)/bin/activate

env:
	@test -f $(BACKEND)/.env || (cp $(BACKEND)/.env.example $(BACKEND)/.env && echo "Copied $(BACKEND)/.env.example -> $(BACKEND)/.env")

seed: install
	cd $(BACKEND) && ../$(PY) -m app.seed

test: install-dev
	cd $(BACKEND) && ../$(PY) -m pytest tests/ -v --tb=short

install-dev: $(VENV)/bin/pytest

$(VENV)/bin/pytest: $(BACKEND)/requirements-dev.txt
	@test -f $(VENV)/bin/activate || (echo "Run make install first" && exit 1)
	$(PIP) install -q -r $(BACKEND)/requirements-dev.txt
	@touch $(VENV)/bin/pytest

run: install
	cd $(BACKEND) && ../$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

reset:
	rm -f $(BACKEND)/foyre.db

clean: reset
	rm -f $(VENV)/bin/pytest
	rm -rf $(VENV)

front-install: $(FRONTEND)/node_modules

$(FRONTEND)/node_modules: $(FRONTEND)/package.json
	cd $(FRONTEND) && npm install
	@touch $(FRONTEND)/node_modules

front: front-install
	cd $(FRONTEND) && npm run dev -- --host 0.0.0.0
