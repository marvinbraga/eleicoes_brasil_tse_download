"""Baixa as urnas do 1º turno de 2026, uma UF por vez, gravando log.

Uso, na raiz do projeto:

    uv run python scripts/baixar_urnas_2026.py

Rodar de novo continua de onde parou. Arquivo já gravado é ignorado.
"""

import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from fcntl import LOCK_EX, LOCK_NB, flock
from pathlib import Path
from typing import TextIO

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from eleicoes.composition.cli import main  # noqa: E402
from eleicoes.domain.report import EXIT_NOT_PUBLISHED, EXIT_SUCCESS  # noqa: E402
from eleicoes.domain.values import UF_CODES  # noqa: E402

ANO = "2026"
TURNO = "1"
_CONTINUA = frozenset({EXIT_SUCCESS, EXIT_NOT_PUBLISHED})


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


def _agora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _registrar(resumo: TextIO, texto: str) -> None:
    linha = f"{_agora()} {texto}\n"
    sys.stdout.write(linha)
    sys.stdout.flush()
    resumo.write(linha)
    resumo.flush()


def _baixar(uf: str, arquivo: Path) -> int:
    with arquivo.open("a", encoding="utf-8") as destino:
        copia_saida = _Copia(sys.stdout, destino)
        copia_erro = _Copia(sys.stderr, destino)
        destino.write(f"\n===== {_agora()} início {uf} =====\n")
        destino.flush()
        with redirect_stdout(copia_saida), redirect_stderr(copia_erro):
            codigo = main(["urnas", "--ano", ANO, "--turno", TURNO, "--uf", uf])
        destino.write(f"===== {_agora()} fim {uf} saída={codigo} =====\n")
        destino.flush()
        return codigo


def _travar(caminho: Path) -> TextIO:
    trava = caminho.open("a", encoding="utf-8")
    try:
        flock(trava.fileno(), LOCK_EX | LOCK_NB)
    except BlockingIOError:
        trava.close()
        print("Já existe uma execução deste script. Espere ela terminar.")
        raise SystemExit(1) from None
    return trava


def executar() -> int:
    os.chdir(RAIZ)
    pasta = RAIZ / "logs" / "urnas-2026"
    pasta.mkdir(parents=True, exist_ok=True)
    trava = _travar(pasta / "execucao.lock")
    try:
        with (pasta / "resumo.log").open("a", encoding="utf-8") as resumo:
            _registrar(resumo, f"início ano={ANO} turno={TURNO} ufs={len(UF_CODES)}")
            _registrar(resumo, f"logs em {pasta}")
            for uf in UF_CODES:
                _registrar(resumo, f"início {uf}")
                codigo = _baixar(uf, pasta / f"{uf}.log")
                _registrar(resumo, f"fim {uf} saída={codigo}")
                if codigo in _CONTINUA:
                    continue
                _registrar(
                    resumo,
                    f"interrompido em {uf}. Rode de novo mais tarde. "
                    "Arquivos já gravados são ignorados.",
                )
                return codigo
            _registrar(resumo, "concluído")
    finally:
        trava.close()
    return EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(executar())
