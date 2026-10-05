#!/bin/sh
# Official entrypoint runs this once, on an empty data directory.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS analise;
SQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
    -v db_owner="$POSTGRES_USER" <<'SQL'
SELECT format('CREATE DATABASE metabase OWNER %I', :'db_owner')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'metabase')\gexec
SQL
