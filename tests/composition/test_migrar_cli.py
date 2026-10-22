from collections.abc import Mapping

import pytest

from eleicoes.adapters.http.errors import http_error
from eleicoes.adapters.orm.migrate import head_revision
from eleicoes.composition.cli import main
from eleicoes.composition.migracao import migrate_database
from eleicoes.domain.errors import SCHEMA_OUTDATED_HINT, DatabaseConfigError, SchemaOutdatedError
from eleicoes.domain.importing import ImportCommand, ImportReport


def test_migrar_prints_the_revision(capsys: pytest.CaptureFixture[str]) -> None:
    seen: list[Mapping[str, str]] = []

    def migrate(env: Mapping[str, str]) -> str:
        seen.append(env)
        return "0002"

    code = main(["migrar"], environ={"POSTGRES_DB": "eleicoes"}, migrate=migrate)
    assert code == 0
    assert seen == [{"POSTGRES_DB": "eleicoes"}]
    assert "Esquema do banco atualizado. Revisão: 0002." in capsys.readouterr().out


def test_migrar_translates_missing_settings(capsys: pytest.CaptureFixture[str]) -> None:
    def migrate(_env: Mapping[str, str]) -> str:
        raise DatabaseConfigError(("POSTGRES_HOST",))

    assert main(["migrar"], environ={}, migrate=migrate) == 1
    assert "Configuração do Postgres incompleta" in capsys.readouterr().err


def test_migrar_hides_driver_errors(capsys: pytest.CaptureFixture[str]) -> None:
    def migrate(_env: Mapping[str, str]) -> str:
        raise RuntimeError("password authentication failed")

    assert main(["migrar"], environ={}, migrate=migrate) == 1
    err = capsys.readouterr().err
    assert "Não foi possível atualizar o esquema do banco." in err
    assert "password" not in err


def test_import_tells_the_user_to_migrate(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["import", "--ano", "2026"], environ={}, importer=_Outdated())
    assert code == 1
    assert "make migrate" in capsys.readouterr().err


def test_migrate_database_uses_the_published_port(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[Mapping[str, str]] = []
    monkeypatch.setattr("eleicoes.composition.migracao.upgrade_database", seen.append)
    monkeypatch.setattr("eleicoes.composition.correspondencia._resolves", lambda _host: False)
    revision = migrate_database(
        {"POSTGRES_HOST": "postgres", "POSTGRES_PORT": "5432", "POSTGRES_PUBLISH_PORT": "25432"}
    )
    assert revision == head_revision()
    assert seen[0]["POSTGRES_HOST"] == "127.0.0.1"
    assert seen[0]["POSTGRES_PORT"] == "25432"


def test_api_answers_503_with_the_migration_hint() -> None:
    assert http_error(SchemaOutdatedError(("0001",), "0002")) == (503, SCHEMA_OUTDATED_HINT)


class _Outdated:
    def execute(self, command: ImportCommand) -> ImportReport:
        del command
        raise SchemaOutdatedError((), "0002")

    def close(self) -> None:
        return None
