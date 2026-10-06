"""Repete o download das urnas de 2026 até concluir.

Uso, na raiz do projeto:

    uv run python scripts/manter_urnas_2026.py

Cada falha espera 3 minutos e roda de novo. Arquivo já gravado é ignorado.
"""

import os
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import datetime
from fcntl import LOCK_EX, LOCK_NB, flock
from pathlib import Path
from typing import TextIO

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from eleicoes.domain.report import EXIT_SUCCESS  # noqa: E402

_ESPERA_SEGUNDOS = 180
_DOWNLOAD = RAIZ / "scripts" / "baixar_urnas_2026.py"


def _agora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _registrar(resumo: TextIO, texto: str) -> None:
    linha = f"{_agora()} {texto}\n"
    sys.stdout.write(linha)
    sys.stdout.flush()
    resumo.write(linha)
    resumo.flush()


def _travar(caminho: Path) -> TextIO:
    trava = caminho.open("a", encoding="utf-8")
    try:
        flock(trava.fileno(), LOCK_EX | LOCK_NB)
    except BlockingIOError:
        trava.close()
        print("Já existe uma execução deste script. Espere ela terminar.")
        raise SystemExit(1) from None
    return trava


def _rodar() -> int:
    ambiente = os.environ.copy()
    ambiente["PYTHONUNBUFFERED"] = "1"
    concluido = subprocess.run(
        [sys.executable, str(_DOWNLOAD)],
        cwd=RAIZ,
        env=ambiente,
        check=False,
    )
    return concluido.returncode


def repetir(
    rodar: Callable[[], int],
    esperar: Callable[[int], None],
    registrar: Callable[[str], None],
) -> int:
    """Roda o download até a saída 0. Qualquer outra saída espera e tenta de novo."""
    registrar("supervisor início")
    while True:
        codigo = rodar()
        if codigo == EXIT_SUCCESS:
            registrar("supervisor concluído")
            return EXIT_SUCCESS
        minutos = _ESPERA_SEGUNDOS // 60
        registrar(f"supervisor saída={codigo}; nova tentativa em {minutos} min")
        esperar(_ESPERA_SEGUNDOS)


def executar() -> int:
    os.chdir(RAIZ)
    pasta = RAIZ / "logs" / "urnas-2026"
    pasta.mkdir(parents=True, exist_ok=True)
    trava = _travar(pasta / "manter.lock")
    try:
        with (pasta / "resumo.log").open("a", encoding="utf-8") as resumo:
            return repetir(_rodar, time.sleep, lambda texto: _registrar(resumo, texto))
    finally:
        trava.close()


if __name__ == "__main__":
    raise SystemExit(executar())
