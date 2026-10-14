SHELL := /bin/bash
VERSION := $(shell cat VERSION)
GIT_SHA := $(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)
IMAGE_TAG ?= $(VERSION)-$(GIT_SHA)
export VERSION IMAGE_TAG
COMPOSE := docker compose
ENV_FILE := .env

.PHONY: up down logs test lint clean reset-data purge-logs backup restore self-test wait config

up: $(ENV_FILE)
	mkdir -p data
	$(COMPOSE) build
	$(COMPOSE) up -d
	$(MAKE) wait

$(ENV_FILE):
	cp -n .env.example .env || true

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200

wait:
	@echo "Waiting for http://127.0.0.1:$${ATEAM_PORT:-8080}/health"
	@for i in $$(seq 1 60); do \
	  if curl -fsS "http://127.0.0.1:$${ATEAM_PORT:-8080}/health" >/dev/null; then \
	    echo "healthy"; exit 0; \
	  fi; \
	  sleep 5; \
	done; \
	echo "timed out waiting for health"; $(COMPOSE) ps; $(COMPOSE) logs --tail=80; exit 1

test:
	pytest -q

lint:
	ruff check app tests scripts

clean:
	$(COMPOSE) down -v --remove-orphans
	rm -rf data .pytest_cache .ruff_cache

# Wipes the postgres-data volume (same as make clean, with a yes prompt).
# Non-interactive: CONFIRM=yes make reset-data
reset-data:
	@if [ "$${CONFIRM}" = "yes" ]; then \
	  $(COMPOSE) down -v --remove-orphans; \
	else \
	  echo "This deletes the postgres-data volume (wizard, users, spend, and the email sink)."; \
	  printf "Type yes to continue: "; \
	  read -r ans; \
	  if [ "$$ans" != "yes" ]; then echo "aborted"; exit 1; fi; \
	  $(COMPOSE) down -v --remove-orphans; \
	fi

purge-logs:
	$(COMPOSE) exec -T postgres psql -U $${POSTGRES_USER:-ateam} -d $${POSTGRES_DB:-ateam} \
	  -c "TRUNCATE spend_events, email_sink RESTART IDENTITY;"

backup:
	mkdir -p backups
	$(COMPOSE) exec -T postgres pg_dump -U $${POSTGRES_USER:-ateam} $${POSTGRES_DB:-ateam} > backups/ateam-latest.sql
	@echo "Wrote backups/ateam-latest.sql (Postgres only; data/secrets.env and data/session.key are not dumped)"

restore:
	test -f backups/ateam-latest.sql
	$(COMPOSE) exec -T postgres psql -U $${POSTGRES_USER:-ateam} -d $${POSTGRES_DB:-ateam} < backups/ateam-latest.sql

self-test:
	curl -fsS http://127.0.0.1:$${ATEAM_PORT:-8080}/api/setup/self-test

config:
	$(COMPOSE) config
