.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help up down restart logs build migrate revision shell psql test e2e lint fmt backup restore-check clean

help:            ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

up:              ## Build if needed and start the site on http://localhost:8000
	@mkdir -p data/media data/backups
	$(COMPOSE) up --build -d
	@echo "→ http://localhost:8000  (admin login at /login)"

down:            ## Stop the stack (photographs on ./data are untouched)
	$(COMPOSE) down

restart:         ## Restart the web container
	$(COMPOSE) restart web

logs:            ## Follow application logs
	$(COMPOSE) logs -f web

build:           ## Rebuild the image without cache
	$(COMPOSE) build --no-cache

migrate:         ## Apply database migrations
	$(COMPOSE) exec web alembic upgrade head

revision:        ## Autogenerate a migration: make revision m="add table"
	$(COMPOSE) exec web alembic revision --autogenerate -m "$(m)"

shell:           ## Shell inside the web container
	$(COMPOSE) exec web bash

psql:            ## psql session on the database
	$(COMPOSE) exec db psql -U $${POSTGRES_USER:-portfolio} -d $${POSTGRES_DB:-portfolio}

test:            ## Run the pytest suite (inside a container, against a real Postgres)
	$(COMPOSE) run --rm tests

e2e:             ## Run Playwright end-to-end tests from the host
	uv run pytest e2e

lint:            ## Ruff lint + format check
	uv run ruff check .
	uv run ruff format --check .

fmt:             ## Ruff autofix + format
	uv run ruff check --fix .
	uv run ruff format .

backup:          ## Dump the database and archive media into ./data/backups
	@bash scripts/backup.sh

restore-check:   ## Rehearse a restore into a scratch database (touches nothing live)
	@bash scripts/restore-check.sh

clean:           ## Stop and remove the database volume (media is NOT deleted)
	$(COMPOSE) down -v
