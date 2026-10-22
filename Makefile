.PHONY: up down import migrate migrate-sql migrate-sql-vazio download-municipais import-municipais

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
	uv run alembic upgrade 0001:head --sql

migrate-sql-vazio:
	uv run alembic upgrade head --sql

download-municipais:
	uv run python -m eleicoes download-municipais --ano 2024 --destino downloads/2024

import-municipais:
	docker compose run --rm --build importer \
		python -m eleicoes import-municipais --ano 2024 --origem /data/downloads/2024
