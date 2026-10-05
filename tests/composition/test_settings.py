from pathlib import Path

import pytest

from eleicoes.composition.command_builder import DownloadCommandBuilder
from eleicoes.composition.settings import build_command, resolve_year
from eleicoes.domain.errors import InvalidElectionYearError, MissingElectionYearError
from eleicoes.domain.values import ElectionYear


def test_cli_year_overrides_the_environment() -> None:
    year = resolve_year(2024, {"ANO_ELEICAO": "2022"})
    assert year == ElectionYear(2024)


def test_environment_year_is_used_when_cli_is_absent() -> None:
    assert resolve_year(None, {"ANO_ELEICAO": " 2022 "}) == ElectionYear(2022)


def test_missing_and_invalid_environment_year() -> None:
    with pytest.raises(MissingElectionYearError):
        resolve_year(None, {})
    with pytest.raises(InvalidElectionYearError):
        resolve_year(None, {"ANO_ELEICAO": "dois mil"})
    with pytest.raises(InvalidElectionYearError):
        resolve_year(1800, {})


def test_command_carries_optional_overrides() -> None:
    command = build_command(
        None,
        None,
        {
            "ANO_ELEICAO": "2022",
            "TSE_URL": '"https://cdn.example/arqurnatot/"',
            "TSE_DATASET_URL": "https://dadosabertos.tse.jus.br/dataset/pacote-2022/",
            "DIRETORIO_SAIDA": "/tmp/tse",
        },
    )
    assert command.request.year == ElectionYear(2022)
    assert command.request.cdn_directory == "https://cdn.example/arqurnatot"
    assert command.request.dataset_ref == "https://dadosabertos.tse.jus.br/dataset/pacote-2022"
    assert command.destination == Path("/tmp/tse")
    assert len(command.request.ufs) == 28
    assert len(command.request.turnos) == 2


def test_cli_destination_overrides_the_environment() -> None:
    command = build_command(
        2026,
        "saida/2026",
        {"ANO_ELEICAO": "2022", "DIRETORIO_SAIDA": "ignorado"},
    )
    assert command.request.year == ElectionYear(2026)
    assert command.destination == Path("saida/2026")


def test_default_destination_includes_the_year() -> None:
    command = build_command(2024, None, {})
    assert command.destination == Path("downloads/2024")


def test_builder_requires_a_year() -> None:
    with pytest.raises(MissingElectionYearError):
        DownloadCommandBuilder().build()


def test_builder_defaults_the_destination_and_ignores_blank_overrides() -> None:
    command = (
        DownloadCommandBuilder()
        .with_year(ElectionYear(2022))
        .with_cdn_directory(None)
        .with_dataset_ref(None)
        .build()
    )
    assert command.destination == Path("downloads/2022")
    assert command.request.cdn_directory is None

    cleared = build_command(2022, "  ", {"TSE_URL": "   ", "TSE_DATASET_URL": ""})
    assert cleared.destination == Path("downloads/2022")
    assert cleared.request.cdn_directory is None
    assert cleared.request.dataset_ref is None
