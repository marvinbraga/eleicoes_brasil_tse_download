import argparse
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import NoReturn, cast

from dotenv import load_dotenv

from eleicoes.composition.migracao import migrate_database
from eleicoes.composition.settings import (
    build_boletim_command,
    build_command,
    build_import_command,
    build_municipal_download_command,
    build_municipal_import_command,
    build_urna_command,
    resolve_destination,
    resolve_year,
)
from eleicoes.composition.wiring import (
    build_app,
    build_boletim_import,
    build_import,
    build_municipal_download,
    build_municipal_import,
    build_urna_download,
)
from eleicoes.domain.boletim import BoletimImportReport
from eleicoes.domain.errors import (
    SCHEMA_OUTDATED_HINT,
    AnnouncedFilesMissingError,
    DatabaseConfigError,
    DuplicateMayorError,
    ElectionError,
    InvalidBoletimError,
    InvalidElectionYearError,
    InvalidMunicipalRowError,
    InvalidMunicipalYearError,
    InvalidPackageRefError,
    InvalidTurnoError,
    InvalidUfError,
    MissingElectionYearError,
    SchemaOutdatedError,
    TransportError,
    TseBlockedError,
    UnexpectedHttpStatusError,
    UnexpectedTsePayloadError,
)
from eleicoes.domain.importing import ImportReport, ImportStatus
from eleicoes.domain.layout import write_index
from eleicoes.domain.municipais import MunicipalImportReport
from eleicoes.domain.report import EXIT_FAILURE, EXIT_NOT_PUBLISHED, EXIT_SUCCESS, RunReport
from eleicoes.domain.urna_models import UrnaRunReport
from eleicoes.domain.values import ElectionYear, Turno, Uf
from eleicoes.ports.boletim import BoletimImporter
from eleicoes.ports.download import ElectionDownloader
from eleicoes.ports.importer import ElectionImporter
from eleicoes.ports.municipais import MunicipalImporter
from eleicoes.ports.urna import UrnaDownloader
from eleicoes.use_cases.list_ausentes import list_ausentes

_MISSING_SHOWN = 3
_DATABASE_CONFIG = (
    "Configuração do Postgres incompleta. Defina POSTGRES_HOST, POSTGRES_PORT, "
    "POSTGRES_USER, POSTGRES_PASSWORD e POSTGRES_DB."
)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        print(f"Erro: {message}", file=sys.stderr)
        raise SystemExit(EXIT_FAILURE)


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    app: ElectionDownloader | None = None,
    importer: ElectionImporter | None = None,
    urnas: UrnaDownloader | None = None,
    boletins: BoletimImporter | None = None,
    migrate: Callable[[Mapping[str, str]], str] | None = None,
    municipal_download: Callable[[bool], ElectionDownloader] | None = None,
    municipal_import: MunicipalImporter | None = None,
) -> int:
    args = _parse(argv)
    if args.command == "download-municipais":
        return _run_municipal_download(args, environ, municipal_download)
    if args.command == "import-municipais":
        return _run_municipal_import(args, environ, municipal_import)
    if args.command == "migrar":
        return _run_migrar(environ, migrate)
    if args.command == "import":
        return _run_import(args, environ, importer)
    if args.command == "urnas":
        return _run_urnas(args, environ, urnas)
    if args.command == "boletins":
        return _run_boletins(args, environ, boletins)
    if args.command == "ausentes":
        return _run_ausentes(args, environ)
    return _run_download(args, environ, app)


def _run_download(
    args: argparse.Namespace,
    environ: Mapping[str, str] | None,
    app: ElectionDownloader | None,
) -> int:
    try:
        command = build_command(
            _year_argument(args),
            _destino_argument(args),
            _environment(environ),
        )
        application = app if app is not None else build_app()
        report = application.execute(command)
        index = _index(command.destination, report)
    except ElectionError as error:
        print(_user_message(error), file=sys.stderr)
        return EXIT_FAILURE
    print(_render(report, index))
    return report.exit_code


def _run_urnas(
    args: argparse.Namespace,
    environ: Mapping[str, str] | None,
    urnas: UrnaDownloader | None,
) -> int:
    try:
        command = build_urna_command(
            _year_argument(args),
            _destino_argument(args),
            _environment(environ),
            turnos=_turnos_argument(args),
            ufs=_ufs_argument(args),
        )
        application = urnas if urnas is not None else build_urna_download()
        report = application.execute(command)
    except ElectionError as error:
        print(_urna_message(error), file=sys.stderr)
        return EXIT_FAILURE
    print(_render_urnas(report))
    return report.exit_code


def _run_boletins(
    args: argparse.Namespace,
    environ: Mapping[str, str] | None,
    boletins: BoletimImporter | None,
) -> int:
    env = _environment(environ)
    try:
        command = build_boletim_command(
            _year_argument(args),
            _optional_turno(args),
            _optional_uf(args),
            env,
        )
        application = boletins if boletins is not None else build_boletim_import(env)
        try:
            report = application.execute(command)
        finally:
            application.close()
    except ElectionError as error:
        print(_boletim_message(error), file=sys.stderr)
        return EXIT_FAILURE
    except Exception:
        print("Não foi possível concluir a importação dos boletins.", file=sys.stderr)
        return EXIT_FAILURE
    print(_render_boletins(report))
    return report.exit_code


def _run_migrar(
    environ: Mapping[str, str] | None,
    migrate: Callable[[Mapping[str, str]], str] | None,
) -> int:
    upgrade = migrate if migrate is not None else migrate_database
    try:
        revision = upgrade(_environment(environ))
    except DatabaseConfigError:
        print(_DATABASE_CONFIG, file=sys.stderr)
        return EXIT_FAILURE
    except Exception:
        print("Não foi possível atualizar o esquema do banco.", file=sys.stderr)
        return EXIT_FAILURE
    print(f"Esquema do banco atualizado. Revisão: {revision}.")
    return EXIT_SUCCESS


def _run_ausentes(
    args: argparse.Namespace,
    environ: Mapping[str, str] | None,
) -> int:
    try:
        year, turno, uf, root = _ausentes_request(args, environ)
        lines = list_ausentes(root, turno, uf)
        report = _write_ausentes_report(year, turno, uf, lines)
    except ElectionError as error:
        print(_ausentes_message(error), file=sys.stderr)
        return EXIT_FAILURE
    print(_render_ausentes(len(lines), report))
    return EXIT_SUCCESS


def _ausentes_request(
    args: argparse.Namespace,
    environ: Mapping[str, str] | None,
) -> tuple[ElectionYear, Turno, Uf | None, Path]:
    env = _environment(environ)
    year = resolve_year(_year_argument(args), env)
    raw_turno = _optional_turno(args)
    if raw_turno is None:
        raise InvalidTurnoError(raw_turno)
    raw_uf = _optional_uf(args)
    uf = None if raw_uf is None else Uf(raw_uf)
    return year, Turno(raw_turno), uf, resolve_destination(None, env, year)


def _write_ausentes_report(
    year: ElectionYear,
    turno: Turno,
    uf: Uf | None,
    lines: tuple[str, ...],
) -> Path:
    path = _ausentes_report_path(year, turno, uf)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_ausentes_text(lines), encoding="utf-8")
    return path


def _ausentes_report_path(year: ElectionYear, turno: Turno, uf: Uf | None) -> Path:
    name = f"ausentes-{year.value}-turno-{turno.value}"
    if uf is not None:
        name = f"{name}-{uf.code.lower()}"
    return Path("relatorios") / f"{name}.txt"


def _ausentes_text(lines: tuple[str, ...]) -> str:
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def _render_ausentes(count: int, path: Path) -> str:
    location = path.as_posix()
    if count == 0:
        return f"Nenhum arquivo ausente. Relatório: {location}"
    return f"Arquivos ausentes: {count}. Relatório: {location}"


def _ausentes_message(error: ElectionError) -> str:
    if isinstance(error, InvalidTurnoError):
        return "Turno inválido. Informe 1 ou 2."
    if isinstance(error, InvalidUfError):
        return "UF inválida."
    return _user_message(error)


def _run_import(
    args: argparse.Namespace,
    environ: Mapping[str, str] | None,
    importer: ElectionImporter | None,
) -> int:
    env = _environment(environ)
    try:
        command = build_import_command(_year_argument(args), _origem_argument(args), env)
        application = importer if importer is not None else build_import(env)
        try:
            report = application.execute(command)
        finally:
            application.close()
    except ElectionError as error:
        print(_import_message(error), file=sys.stderr)
        return EXIT_FAILURE
    except Exception:
        print("Não foi possível concluir a importação.", file=sys.stderr)
        return EXIT_FAILURE
    print(_render_import(report))
    return report.exit_code


def _run_municipal_download(
    args: argparse.Namespace,
    environ: Mapping[str, str] | None,
    factory: Callable[[bool], ElectionDownloader] | None,
) -> int:
    try:
        command = build_municipal_download_command(
            _year_argument(args),
            _destino_argument(args),
            _environment(environ),
        )
        build = factory if factory is not None else _municipal_downloader
        report = build(_atualizar_argument(args)).execute(command)
        index = _index(command.destination, report)
    except ElectionError as error:
        print(_user_message(error), file=sys.stderr)
        return EXIT_FAILURE
    print(_render(report, index))
    if report.discovered > 0 and report.missing > 0:
        print(
            "O TSE não listou todos os zips municipais; a importação não reconstrói a análise "
            "sem os três.",
            file=sys.stderr,
        )
        return EXIT_FAILURE
    return report.exit_code


def _municipal_downloader(overwrite: bool) -> ElectionDownloader:
    return build_municipal_download(overwrite=overwrite)


def _atualizar_argument(args: argparse.Namespace) -> bool:
    return cast(object, getattr(args, "atualizar", False)) is True


def _run_municipal_import(
    args: argparse.Namespace,
    environ: Mapping[str, str] | None,
    importer: MunicipalImporter | None,
) -> int:
    env = _environment(environ)
    try:
        command = build_municipal_import_command(_year_argument(args), _origem_argument(args), env)
        application = importer if importer is not None else build_municipal_import(env)
        try:
            report = application.execute(command)
        finally:
            application.close()
    except ElectionError as error:
        print(_import_message(error), file=sys.stderr)
        return EXIT_FAILURE
    except Exception:
        print("Não foi possível concluir a importação.", file=sys.stderr)
        return EXIT_FAILURE
    print(_render_municipal(report))
    return report.exit_code


def _render_municipal(report: MunicipalImportReport) -> str:
    if report.tables.exit_code == EXIT_NOT_PUBLISHED:
        return "Nenhum arquivo municipal para importar. Rode download-municipais antes."
    tables = _render_import(report.tables)
    built = report.results
    if built is None and report.faltando:
        return f"{tables}\n{_missing_members(report.faltando)}"
    if built is None:
        return f"{tables}\nA análise municipal não foi reconstruída por causa das falhas."
    corte = datetime.strptime(built.geracao, "%d%m%Y%H%M")
    return "\n".join(
        (
            tables,
            f"Municípios: {len(built.municipios)}. Prefeitos eleitos: {built.prefeitos}. "
            f"Sem prefeito eleito: {built.sem_prefeito}. Suplementares: {built.suplementares}.",
            f"Vereadores eleitos: {built.vereadores_eleitos}. "
            f"Divergências entre eleitos e vagas: {len(built.divergencias)}.",
            f"Dados do TSE gerados em {corte:%d/%m/%Y} às {corte:%H:%M}.",
        )
    )


def _missing_members(faltando: tuple[str, ...]) -> str:
    shown = ", ".join(faltando[:_MISSING_SHOWN])
    more = "" if len(faltando) <= _MISSING_SHOWN else ", …"
    return (
        f"A análise municipal não foi reconstruída: faltam {len(faltando)} arquivos por UF "
        f"({shown}{more}). Rode download-municipais --atualizar e importe de novo."
    )


def _parse(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = _Parser(
        prog="eleicoes",
        description="Baixa e importa os arquivos abertos de uma eleição do TSE.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser("download", help="Descobre e baixa os zips do ano informado.")
    _add_year(download)
    download.add_argument(
        "--destino",
        default=None,
        help="Pasta de destino. Padrão: downloads/{ano} ou DIRETORIO_SAIDA.",
    )
    incoming = commands.add_parser("import", help="Importa os CSV de correspondência já baixados.")
    _add_year(incoming)
    incoming.add_argument(
        "--origem",
        default=None,
        help="Pasta do ano, com indice.csv. Padrão: downloads/{ano} ou DIRETORIO_SAIDA.",
    )
    municipal = commands.add_parser(
        "download-municipais",
        help="Baixa consulta_cand, consulta_vagas e detalhe_votacao_munzona da eleição municipal.",
        description=(
            "Baixa só os três zips municipais do TSE e grava downloads/{ano}/indice.csv. "
            "Não use download --ano 2024: ele baixaria gigabytes de boletins de urna e "
            "regravaria o mesmo indice.csv sem os zips municipais."
        ),
    )
    _add_year(municipal)
    municipal.add_argument(
        "--destino", default=None, help="Pasta de destino. Padrão: downloads/{ano}."
    )
    municipal.add_argument(
        "--atualizar",
        action="store_true",
        help="Baixa de novo mesmo se o zip já existir (o TSE regera os arquivos todo dia).",
    )
    municipal_in = commands.add_parser(
        "import-municipais",
        help="Importa os CSV municipais baixados e reconstrói prefeitos e vereadores eleitos.",
    )
    _add_year(municipal_in)
    municipal_in.add_argument("--origem", default=None, help="Pasta do ano, com indice.csv.")
    boxes = commands.add_parser("urnas", help="Baixa os arquivos de urna de cada seção.")
    _add_urnas(boxes)
    bulletins = commands.add_parser(
        "boletins",
        help="Importa os boletins de urna (bu.dat) de uma UF.",
    )
    _add_year(bulletins)
    bulletins.add_argument("--turno", type=int, default=None, help="Turno 1 ou 2.")
    bulletins.add_argument("--uf", default=None, help="Sigla da UF.")
    commands.add_parser(
        "migrar",
        help="Cria ou atualiza o esquema do Postgres com as migrações do Alembic.",
    )
    missing = commands.add_parser(
        "ausentes",
        help="Lista os arquivos de urna marcados como ausentes, sem baixar nem importar.",
    )
    _add_year(missing)
    missing.add_argument("--turno", type=int, default=None, help="Turno 1 ou 2.")
    missing.add_argument("--uf", default=None, help="Sigla da UF. Padrão: todas.")
    if argv is None:
        return parser.parse_args()
    return parser.parse_args(list(argv))


def _add_urnas(parser: argparse.ArgumentParser) -> None:
    _add_year(parser)
    parser.add_argument(
        "--destino",
        default=None,
        help="Pasta de destino. Padrão: downloads/{ano} ou DIRETORIO_SAIDA.",
    )
    parser.add_argument(
        "--turno",
        action="append",
        type=int,
        default=None,
        help="Turno 1 ou 2. Pode repetir. Padrão: os dois.",
    )
    parser.add_argument(
        "--uf",
        action="append",
        default=None,
        help="Sigla da UF. Pode repetir. Padrão: todas.",
    )


def _add_year(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--ano",
        type=int,
        default=None,
        help="Ano da eleição. Sobrescreve ANO_ELEICAO.",
    )


def _environment(environ: Mapping[str, str] | None) -> Mapping[str, str]:
    if environ is not None:
        return environ
    load_dotenv()
    return os.environ


def _year_argument(args: argparse.Namespace) -> int | None:
    value = cast(object, getattr(args, "ano", None))
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise InvalidElectionYearError(value)


def _turnos_argument(args: argparse.Namespace) -> tuple[int, ...] | None:
    value = cast(object, getattr(args, "turno", None))
    if value is None:
        return None
    if not isinstance(value, list):
        raise InvalidTurnoError(value)
    numbers: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int):
            raise InvalidTurnoError(item)
        numbers.append(item)
    return tuple(numbers)


def _ufs_argument(args: argparse.Namespace) -> tuple[str, ...] | None:
    value = cast(object, getattr(args, "uf", None))
    if value is None:
        return None
    if not isinstance(value, list):
        raise InvalidUfError(value)
    codes: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise InvalidUfError(item)
        codes.append(item)
    return tuple(codes)


def _optional_turno(args: argparse.Namespace) -> int | None:
    value = cast(object, getattr(args, "turno", None))
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidTurnoError(value)
    return value


def _optional_uf(args: argparse.Namespace) -> str | None:
    value = cast(object, getattr(args, "uf", None))
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidUfError(value)
    return value


def _destino_argument(args: argparse.Namespace) -> str | None:
    return _text_argument(args, "destino")


def _origem_argument(args: argparse.Namespace) -> str | None:
    return _text_argument(args, "origem")


def _text_argument(args: argparse.Namespace, name: str) -> str | None:
    value = cast(object, getattr(args, name, None))
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise ElectionError(f"{name} inválido")


def _boletim_message(error: ElectionError) -> str:
    if isinstance(error, InvalidBoletimError):
        return f"Boletim inválido: {error.arquivo}."
    if isinstance(error, DatabaseConfigError):
        return _DATABASE_CONFIG
    if isinstance(error, SchemaOutdatedError):
        return SCHEMA_OUTDATED_HINT
    if isinstance(error, InvalidTurnoError):
        return "Turno inválido. Informe 1 ou 2."
    if isinstance(error, InvalidUfError):
        return "UF inválida."
    if isinstance(error, (InvalidElectionYearError, MissingElectionYearError)):
        return _user_message(error)
    return "Não foi possível concluir a importação dos boletins."


def _render_boletins(report: BoletimImportReport) -> str:
    if report.exit_code == EXIT_NOT_PUBLISHED:
        return "Nenhum boletim de urna encontrado."
    summary = f"Boletins gravados: {report.boletins}. Votos: {report.votos}."
    if not report.ausentes:
        return summary
    lines = [f"[ausente] {name}" for name in report.ausentes]
    lines.append(summary)
    return "\n".join(lines)


def _import_message(error: ElectionError) -> str:
    if isinstance(error, InvalidMunicipalYearError):
        return _user_message(error)
    if isinstance(error, DuplicateMayorError):
        return f"Há mais de um prefeito eleito em {error.uf} {error.ue}. Confira o consulta_cand."
    if isinstance(error, InvalidMunicipalRowError):
        return f"Valor inesperado no campo {error.field} dos dados municipais."
    if isinstance(error, DatabaseConfigError):
        return _DATABASE_CONFIG
    if isinstance(error, SchemaOutdatedError):
        return SCHEMA_OUTDATED_HINT
    if isinstance(error, (InvalidElectionYearError, MissingElectionYearError)):
        return _user_message(error)
    return "Não foi possível concluir a importação."


def _render_import(report: ImportReport) -> str:
    if report.exit_code == EXIT_NOT_PUBLISHED:
        return "Nenhum arquivo tabular para importar."
    loaded = report.count(ImportStatus.LOADED)
    ignored = report.count(ImportStatus.IGNORED)
    failed = report.count(ImportStatus.FAILED)
    lines = [
        (
            f"Importação concluída: {loaded} tabelas, "
            f"{report.loaded_rows} linhas, {ignored} ignorados."
        ),
        f"Falhas: {failed}",
    ]
    return "\n".join(lines)


def _urna_message(error: ElectionError) -> str:
    if isinstance(error, InvalidTurnoError):
        return "Turno inválido. Informe 1 ou 2."
    if isinstance(error, InvalidUfError):
        return "UF inválida."
    if isinstance(error, (TseBlockedError, AnnouncedFilesMissingError, UnexpectedTsePayloadError)):
        return str(error)
    return _user_message(error)


def _render_urnas(report: UrnaRunReport) -> str:
    lines: list[str] = []
    notice = "O TSE ainda não publicou os arquivos de urna deste turno."
    if report.unpublished_turnos or report.exit_code == EXIT_NOT_PUBLISHED:
        lines.append(notice)
    if report.exit_code == EXIT_NOT_PUBLISHED:
        return "\n".join(lines)
    lines.extend(
        [
            f"Arquivos encontrados: {report.discovered}",
            f"Baixados: {report.downloaded}",
            f"Ignorados: {report.skipped}",
            f"Ausentes: {report.missing}",
        ]
    )
    return "\n".join(lines)


def _user_message(error: ElectionError) -> str:
    if isinstance(error, InvalidMunicipalYearError):
        return "Ano sem eleição municipal. Informe um ano como 2024."
    if isinstance(error, InvalidElectionYearError):
        return "Ano inválido. Informe um ano entre 1994 e 2100."
    if isinstance(error, MissingElectionYearError):
        return "Informe o ano com --ano ou defina a variável ANO_ELEICAO."
    if isinstance(error, InvalidPackageRefError):
        return "A referência do conjunto de dados em TSE_DATASET_URL é inválida."
    if isinstance(error, UnexpectedHttpStatusError):
        return f"Falha ao baixar {error.filename}: HTTP {error.status_code}."
    if isinstance(error, TransportError):
        return "Falha de rede ou de disco ao acessar os arquivos do TSE."
    return "Não foi possível concluir o download."


def _index(destination: Path, report: RunReport) -> Path | None:
    if report.discovered == 0:
        return None
    return write_index(destination, report.outcomes)


def _render(report: RunReport, index: Path | None) -> str:
    if report.discovered == 0:
        return "Nenhum arquivo publicado para o ano informado."
    lines = [
        f"Arquivos encontrados: {report.discovered}",
        f"Baixados: {report.downloaded}",
        f"Ignorados: {report.skipped}",
        f"Ausentes: {report.missing}",
    ]
    if index is not None:
        lines.append(f"Índice: {index}")
    return "\n".join(lines)
