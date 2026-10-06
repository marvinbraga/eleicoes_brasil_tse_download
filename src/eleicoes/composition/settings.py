from collections.abc import Mapping, Sequence
from pathlib import Path

from eleicoes.composition.command_builder import DownloadCommandBuilder
from eleicoes.composition.import_command_builder import ImportCommandBuilder
from eleicoes.domain.boletim import ImportBoletinsCommand
from eleicoes.domain.command import DownloadCommand
from eleicoes.domain.errors import (
    EmptyElectionScopeError,
    InvalidElectionYearError,
    InvalidTurnoError,
    InvalidUfError,
    MissingElectionYearError,
)
from eleicoes.domain.importing import ImportCommand
from eleicoes.domain.urna_models import URNA_COLLECTION, UrnaDownloadCommand
from eleicoes.domain.values import ElectionYear, Turno, Uf, default_turnos, default_ufs


def resolve_year(cli_year: int | None, env: Mapping[str, str]) -> ElectionYear:
    if cli_year is not None:
        return ElectionYear(cli_year)
    raw = _clean(env.get("ANO_ELEICAO"))
    if raw is None:
        raise MissingElectionYearError()
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise InvalidElectionYearError(raw) from exc
    return ElectionYear(parsed)


def resolve_destination(
    cli_destino: str | None,
    env: Mapping[str, str],
    year: ElectionYear,
) -> Path:
    chosen = _clean(cli_destino)
    if chosen is None:
        chosen = _clean(env.get("DIRETORIO_SAIDA"))
    if chosen is None:
        return Path("downloads") / str(year.value)
    return Path(chosen)


def resolve_origin(cli_origem: str | None, env: Mapping[str, str], year: ElectionYear) -> Path:
    """Argumento, DIRETORIO_SAIDA, ou downloads/{ano}. Não grava essa variável no .env."""
    return resolve_destination(cli_origem, env, year)


def build_import_command(
    cli_year: int | None,
    cli_origem: str | None,
    env: Mapping[str, str],
) -> ImportCommand:
    year = resolve_year(cli_year, env)
    return (
        ImportCommandBuilder()
        .with_year(year)
        .with_origin(resolve_origin(cli_origem, env, year))
        .build()
    )


def build_command(
    cli_year: int | None,
    cli_destino: str | None,
    env: Mapping[str, str],
) -> DownloadCommand:
    year = resolve_year(cli_year, env)
    return (
        DownloadCommandBuilder()
        .with_year(year)
        .with_cdn_directory(_clean(env.get("TSE_URL")))
        .with_dataset_ref(_clean(env.get("TSE_DATASET_URL")))
        .with_destination(resolve_destination(cli_destino, env, year))
        .build()
    )


def build_urna_command(
    cli_year: int | None,
    cli_destino: str | None,
    env: Mapping[str, str],
    turnos: Sequence[int] | None = None,
    ufs: Sequence[str] | None = None,
) -> UrnaDownloadCommand:
    year = resolve_year(cli_year, env)
    return UrnaDownloadCommand(
        year=year,
        turnos=_scoped_turnos(turnos),
        ufs=_scoped_ufs(ufs),
        destination=resolve_destination(cli_destino, env, year),
    )


def build_boletim_command(
    cli_year: int | None,
    cli_turno: int | None,
    cli_uf: str | None,
    env: Mapping[str, str],
) -> ImportBoletinsCommand:
    year = resolve_year(cli_year, env)
    if cli_turno is None:
        raise InvalidTurnoError(cli_turno)
    if not isinstance(cli_uf, str):
        raise InvalidUfError(cli_uf)
    turno = Turno(cli_turno)
    uf = Uf(cli_uf)
    root = resolve_destination(None, env, year)
    origin = root / URNA_COLLECTION / f"turno-{turno.value}" / uf.code
    return ImportBoletinsCommand(year=year, turno=turno, uf=uf, origin=origin)


def _scoped_turnos(raw: Sequence[int] | None) -> tuple[Turno, ...]:
    if raw is None:
        return default_turnos()
    chosen: list[Turno] = []
    seen: set[int] = set()
    for value in raw:
        turno = Turno(value)
        if turno.value in seen:
            continue
        seen.add(turno.value)
        chosen.append(turno)
    if not chosen:
        raise EmptyElectionScopeError("turno")
    return tuple(chosen)


def _scoped_ufs(raw: Sequence[str] | None) -> tuple[Uf, ...]:
    if raw is None:
        return default_ufs()
    chosen: list[Uf] = []
    seen: set[str] = set()
    for value in raw:
        if not isinstance(value, str):
            raise InvalidUfError(value)
        uf = Uf(value)
        if uf.code in seen:
            continue
        seen.add(uf.code)
        chosen.append(uf)
    if not chosen:
        raise EmptyElectionScopeError("UF")
    return tuple(chosen)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip().strip('"').strip("'")
    if not stripped:
        return None
    return stripped
