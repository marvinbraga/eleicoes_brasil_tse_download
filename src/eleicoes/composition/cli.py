import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NoReturn, cast

from dotenv import load_dotenv

from eleicoes.composition.settings import build_command, build_import_command
from eleicoes.composition.wiring import build_app, build_import
from eleicoes.domain.errors import (
    DatabaseConfigError,
    ElectionError,
    InvalidElectionYearError,
    InvalidPackageRefError,
    MissingElectionYearError,
    TransportError,
    UnexpectedHttpStatusError,
)
from eleicoes.domain.importing import ImportReport, ImportStatus
from eleicoes.domain.layout import write_index
from eleicoes.domain.report import EXIT_FAILURE, EXIT_NOT_PUBLISHED, RunReport
from eleicoes.ports.download import ElectionDownloader
from eleicoes.ports.importer import ElectionImporter


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
) -> int:
    args = _parse(argv)
    if args.command == "import":
        return _run_import(args, environ, importer)
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
    if argv is None:
        return parser.parse_args()
    return parser.parse_args(list(argv))


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


def _import_message(error: ElectionError) -> str:
    if isinstance(error, DatabaseConfigError):
        return (
            "Configuração do Postgres incompleta. Defina POSTGRES_HOST, POSTGRES_PORT, "
            "POSTGRES_USER, POSTGRES_PASSWORD e POSTGRES_DB."
        )
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


def _user_message(error: ElectionError) -> str:
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
