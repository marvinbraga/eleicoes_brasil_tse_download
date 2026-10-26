"""Acompanha o download do 2º turno de 2026, importa cada UF que termina e refaz o mapa.

Uso, na raiz do projeto, com o download rodando em outro terminal:

    uv run python scripts/acompanhar_turno_2026.py                  # repete a cada 120 s
    uv run python scripts/acompanhar_turno_2026.py --intervalo 300
    uv run python scripts/acompanhar_turno_2026.py --uma-vez        # uma passada só

Lê logs/urnas-2026-turno-2/resumo.log. Uma UF cuja última linha é "fim XX saída=0" e que
ainda não foi importada depois dessa linha é importada. As importações ficam em
importados.log, na mesma pasta. Para quando as 27 UFs e o exterior (ZZ) estão importados.
"""

import argparse
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime
from fcntl import LOCK_EX, LOCK_NB, flock
from pathlib import Path
from typing import Final, TextIO

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS  # noqa: E402
from eleicoes.domain.values import UF_CODES  # noqa: E402

ANO: Final = "2026"
TURNO: Final = "2"
PASTA: Final = RAIZ / "logs" / f"urnas-{ANO}-turno-{TURNO}"
INTERVALO_PADRAO: Final = 120
_INTERROMPIDO: Final = 130
_EVENTO: Final = re.compile(
    r"^(?P<momento>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) "
    r"(?P<tipo>início|fim) (?P<uf>[A-Z]{2})(?: saída=(?P<saida>-?\d+))?$"
)
_IMPORTADA: Final = re.compile(r"^\S+ \S+ (?P<uf>[A-Z]{2}) fim=(?P<fim>\S+ \S+) (?P<arquivos>.+)$")
_BOLETIM: Final = "*/*/*/*-bu.dat"
_AUSENTE: Final = "*.ausente"


@dataclass(frozen=True, slots=True)
class Fim:
    uf: str
    momento: str


@dataclass(frozen=True, slots=True)
class Importada:
    uf: str
    fim: str
    arquivos: str


class _Copia:
    """Escreve cada linha no terminal e no arquivo de log."""

    def __init__(self, terminal: TextIO, arquivo: TextIO) -> None:
        self._terminal = terminal
        self._arquivo = arquivo

    def write(self, texto: str) -> int:
        self._terminal.write(texto)
        self._arquivo.write(texto)
        self.flush()
        return len(texto)

    def flush(self) -> None:
        self._terminal.flush()
        self._arquivo.flush()


def ler_fins(texto: str) -> dict[str, Fim]:
    """UFs cujo último evento é "fim XX saída=0". Um "início" depois dele tira a UF."""
    ultimo: dict[str, Fim | None] = {}
    for linha in texto.splitlines():
        achado = _EVENTO.match(linha.strip())
        if achado is None:
            continue
        uf = achado["uf"]
        concluiu = achado["tipo"] == "fim" and achado["saida"] == "0"
        ultimo[uf] = Fim(uf, achado["momento"]) if concluiu else None
    return {uf: fim for uf, fim in ultimo.items() if fim is not None}


def ler_importadas(texto: str) -> dict[str, Importada]:
    """A última linha de cada UF em importados.log vale."""
    importadas: dict[str, Importada] = {}
    for linha in texto.splitlines():
        achado = _IMPORTADA.match(linha.strip())
        if achado is not None:
            uf = achado["uf"]
            importadas[uf] = Importada(uf, achado["fim"], achado["arquivos"])
    return importadas


def pendentes(fins: Mapping[str, Fim], importadas: Mapping[str, Importada]) -> tuple[Fim, ...]:
    """UFs com um "fim" mais novo que o da última importação, na ordem do download."""
    novas: list[Fim] = []
    for uf in UF_CODES:
        fim = fins.get(uf)
        if fim is None:
            continue
        anterior = importadas.get(uf)
        if anterior is None or fim.momento > anterior.fim:
            novas.append(fim)
    return tuple(novas)


def completo(importadas: Mapping[str, Importada], faltam: tuple[Fim, ...]) -> bool:
    return not faltam and all(uf in importadas for uf in UF_CODES)


def assinatura(origem: Path) -> str:
    """Conta boletins e ausentes da UF. Um ausente que chega muda as duas contas."""
    if not origem.is_dir():
        return "boletins=0 ausentes=0"
    boletins = sum(1 for caminho in origem.glob(_BOLETIM) if caminho.is_file())
    ausentes = sum(1 for caminho in origem.rglob(_AUSENTE) if caminho.is_file())
    return f"boletins={boletins} ausentes={ausentes}"


@dataclass(slots=True)
class Passada:
    """Uma leitura dos logs. Devolve quantas UFs foram importadas com sucesso."""

    pasta: Path
    importar: Callable[[str], int]
    assinar: Callable[[str], str]
    registrar: Callable[[str], None]
    agora: Callable[[], str]

    def __call__(self, tentadas: set[Fim]) -> int:
        importadas = ler_importadas(_ler(self.pasta / "importados.log"))
        fins = ler_fins(_ler(self.pasta / "resumo.log"))
        sucesso = 0
        for fim in pendentes(fins, importadas):
            if fim in tentadas:
                continue
            sucesso += self._uma(fim, importadas.get(fim.uf), tentadas)
        return sucesso

    def concluiu(self) -> bool:
        importadas = ler_importadas(_ler(self.pasta / "importados.log"))
        fins = ler_fins(_ler(self.pasta / "resumo.log"))
        return completo(importadas, pendentes(fins, importadas))

    def _uma(self, fim: Fim, anterior: Importada | None, tentadas: set[Fim]) -> int:
        arquivos = self.assinar(fim.uf)
        if anterior is not None and anterior.arquivos == arquivos:
            # O download passou de novo pela UF sem trazer arquivo novo: só anota o fim.
            self._anotar(Importada(fim.uf, fim.momento, arquivos))
            self.registrar(f"{fim.uf} sem arquivos novos ({arquivos})")
            return 0
        self.registrar(f"importando {fim.uf} ({arquivos})")
        codigo = self.importar(fim.uf)
        if codigo != EXIT_SUCCESS:
            # Não tenta de novo o mesmo fim; um novo "fim" no resumo libera outra tentativa.
            tentadas.add(fim)
            self.registrar(f"falha ao importar {fim.uf} saída={codigo}")
            return 0
        self._anotar(Importada(fim.uf, fim.momento, arquivos))
        self.registrar(f"importado {fim.uf}")
        return 1

    def _anotar(self, item: Importada) -> None:
        with (self.pasta / "importados.log").open("a", encoding="utf-8") as destino:
            destino.write(f"{self.agora()} {item.uf} fim={item.fim} {item.arquivos}\n")


def acompanhar(
    passada: Passada,
    gerar_mapa: Callable[[], int],
    esperar: Callable[[int], None],
    intervalo: int,
    *,
    uma_vez: bool = False,
) -> int:
    """Importa o que terminou, refaz o mapa uma vez por lote e espera a próxima passada."""
    registrar = passada.registrar
    registrar(f"acompanhamento início ano={ANO} turno={TURNO} intervalo={intervalo}s")
    tentadas: set[Fim] = set()
    while True:
        if passada(tentadas) > 0:
            registrar("gerando o mapa de presidente")
            registrar(f"mapa saída={gerar_mapa()}")
        if passada.concluiu():
            registrar(f"concluído: {len(UF_CODES)} UFs importadas")
            return EXIT_SUCCESS
        if uma_vez:
            return EXIT_SUCCESS
        esperar(intervalo)


def _ler(caminho: Path) -> str:
    try:
        return caminho.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _agora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _registrar(log: TextIO, texto: str) -> None:
    linha = f"{_agora()} {texto}\n"
    sys.stdout.write(linha)
    sys.stdout.flush()
    log.write(linha)
    log.flush()


def rodar_com_log(arquivo: Path, rodar: Callable[[], int], titulo: str) -> int:
    """Roda no mesmo processo, copiando a saída para o log. Uma exceção vira saída 1."""
    with arquivo.open("a", encoding="utf-8") as destino:
        destino.write(f"\n===== {_agora()} início {titulo} =====\n")
        destino.flush()
        with (
            redirect_stdout(_Copia(sys.stdout, destino)),
            redirect_stderr(_Copia(sys.stderr, destino)),
        ):
            try:
                codigo = rodar()
            except SystemExit as saida:
                codigo = saida.code if isinstance(saida.code, int) else EXIT_FAILURE
            except Exception as erro:  # uma UF ruim não derruba o laço
                print(f"Erro inesperado: {erro!r}", file=sys.stderr)
                codigo = EXIT_FAILURE
        destino.write(f"===== {_agora()} fim {titulo} saída={codigo} =====\n")
        destino.flush()
    return codigo


def _importar(uf: str) -> int:
    from eleicoes.composition.cli import main

    argumentos = ["boletins", "--ano", ANO, "--turno", TURNO, "--uf", uf]
    return rodar_com_log(PASTA / f"importar-{uf}.log", lambda: main(argumentos), uf)


def _gerar_mapa() -> int:
    """Refaz o mapa dos dois turnos e põe o relatório de seções para rodar ao lado.

    Cada mapa roda num processo novo: assim ele usa o código atual do projeto, e não o que
    este script carregou quando começou. O relatório de seções lê o banco seção a seção e
    pode levar muito tempo em UF grande; ele não segura a próxima importação.
    """
    codigos = []
    for turno in ("1", "2"):
        with (PASTA / "mapa.log").open("a", encoding="utf-8") as destino:
            destino.write(f"\n===== {_agora()} início mapa turno {turno} =====\n")
            destino.flush()
            codigo = subprocess.run(  # noqa: S603 - comando fixo, sem entrada externa
                [
                    sys.executable,
                    str(RAIZ / "scripts" / "relatorio_mapa.py"),
                    "--ano",
                    ANO,
                    "--turno",
                    turno,
                    "--cargo",
                    "presidente",
                    "--sem-navegador",
                ],
                cwd=RAIZ,
                stdout=destino,
                stderr=subprocess.STDOUT,
                check=False,
            ).returncode
            destino.write(f"===== {_agora()} fim mapa turno {turno} saída={codigo} =====\n")
        codigos.append(codigo)
    _secoes_ao_lado()
    return next((codigo for codigo in codigos if codigo != 0), 0)


def _secoes_ao_lado() -> None:
    """Uma cópia por vez, mesmo entre reinícios deste script (flock), e com o disco em
    prioridade ociosa (ionice): o relatório de seções não atrasa o mapa nem a importação."""
    with (PASTA / "secoes.log").open("a", encoding="utf-8") as destino:
        destino.write(f"\n===== {_agora()} início seções =====\n")
        destino.flush()
        subprocess.Popen(  # noqa: S603 - comando fixo, sem entrada externa
            [
                "flock",
                "--nonblock",
                str(PASTA / "secoes.lock"),
                "ionice",
                "-c3",
                sys.executable,
                str(RAIZ / "scripts" / "relatorio_secoes_turnos.py"),
                "--ano",
                ANO,
                "--sem-navegador",
            ],
            cwd=RAIZ,
            stdout=destino,
            stderr=subprocess.STDOUT,
        )


def _assinar(uf: str) -> str:
    from eleicoes.composition.settings import build_boletim_command

    comando = build_boletim_command(int(ANO), int(TURNO), uf, os.environ)
    return assinatura(comando.origin)


def _travar(caminho: Path) -> TextIO:
    trava = caminho.open("a", encoding="utf-8")
    try:
        flock(trava.fileno(), LOCK_EX | LOCK_NB)
    except BlockingIOError:
        trava.close()
        print("Já existe uma execução deste script. Espere ela terminar.")
        raise SystemExit(1) from None
    return trava


def ler_opcoes(argumentos: list[str]) -> argparse.Namespace:
    leitor = argparse.ArgumentParser(
        description="Importa cada UF do 2º turno de 2026 que termina de baixar e refaz o mapa."
    )
    leitor.add_argument(
        "--intervalo",
        type=int,
        default=INTERVALO_PADRAO,
        help=f"Segundos entre as passadas. Padrão: {INTERVALO_PADRAO}.",
    )
    leitor.add_argument("--uma-vez", action="store_true", help="Faz uma passada e sai.")
    opcoes = leitor.parse_args(argumentos)
    if opcoes.intervalo < 1:
        leitor.error("--intervalo precisa ser maior que zero.")
    return opcoes


def executar(argumentos: list[str] | None = None) -> int:
    opcoes = ler_opcoes(sys.argv[1:] if argumentos is None else argumentos)
    os.chdir(RAIZ)
    from dotenv import load_dotenv

    load_dotenv()
    PASTA.mkdir(parents=True, exist_ok=True)
    trava = _travar(PASTA / "acompanhar.lock")
    try:
        with (PASTA / "acompanhar.log").open("a", encoding="utf-8") as log:

            def registrar(texto: str) -> None:
                _registrar(log, texto)

            passada = Passada(PASTA, _importar, _assinar, registrar, _agora)
            try:
                return acompanhar(
                    passada, _gerar_mapa, time.sleep, opcoes.intervalo, uma_vez=opcoes.uma_vez
                )
            except KeyboardInterrupt:
                registrar("interrompido pelo usuário")
                return _INTERROMPIDO
    finally:
        trava.close()


if __name__ == "__main__":
    raise SystemExit(executar())
