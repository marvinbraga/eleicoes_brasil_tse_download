.PHONY: up down import migrate migrate-sql

up:
	docker compose up -d --build

down:
	docker compose down

import:
	docker compose run --rm --build importer \
		python -m eleicoes import --ano 2026 --origem /data/downloads/2026

migrate:
	docker compose run --rm --build importer python -m eleicoes migrar

migrate-sql:
	uv run alembic upgrade head --sql
