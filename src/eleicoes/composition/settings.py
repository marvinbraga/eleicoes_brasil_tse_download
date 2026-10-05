from collections.abc import Mapping
from pathlib import Path

from eleicoes.composition.command_builder import DownloadCommandBuilder
from eleicoes.domain.command import DownloadCommand
from eleicoes.domain.errors import InvalidElectionYearError, MissingElectionYearError
from eleicoes.domain.values import ElectionYear


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


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip().strip('"').strip("'")
    if not stripped:
        return None
    return stripped
