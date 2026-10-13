"""Baixa as malhas medidas para o mapa.

Uso, na raiz do projeto:

    uv run python scripts/baixar_malha.py
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS  # noqa: E402
from eleicoes.use_cases.baixar_malha import MeshSizeError, baixar_malha  # noqa: E402

_DESTINO: Final = Path("downloads/malha")
_TIMEOUT_SECONDS: Final = 120


def main(argv: Sequence[str] | None = None) -> int:
    _parser().parse_args(argv)
    try:
        baixar_malha(_DESTINO, _conteudo)
    except MeshSizeError:
        print("A malha baixada não confere com a especificação.", file=sys.stderr)
        return EXIT_FAILURE
    print("Malha gravada em downloads/malha.")
    print(
        "As cores e as logomarcas ficam em downloads/malha/marcas.json "
        "e downloads/malha/logomarcas/."
    )
    return EXIT_SUCCESS


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(description="Baixa as malhas medidas para downloads/malha.")


def _conteudo(url: str) -> bytes:
    return requests.get(url, timeout=_TIMEOUT_SECONDS).content


if __name__ == "__main__":
    raise SystemExit(main())
