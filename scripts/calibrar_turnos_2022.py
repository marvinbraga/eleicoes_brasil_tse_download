"""Calibra os limiares do 1º × 2º turno de presidente com a eleição de 2022.

Baixa dos dados abertos do TSE os zips munzona de 2022 (só se ainda não
estiverem na pasta), roda a conta do mapa em cada cenário com o 22 como
apoiado e grava dados/calibracao_turnos_2022.json.

Uso, na raiz do projeto:

    uv run python scripts/calibrar_turnos_2022.py [--pasta downloads/2022-calibracao]
"""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from eleicoes.adapters.munzona_presidente import (  # noqa: E402
    DETALHE_DA_VOTACAO,
    VOTOS_POR_CANDIDATO,
    ler_presidente_munzona,
    url_munzona,
)
from eleicoes.adapters.requests_http import RequestsHttpClient  # noqa: E402
from eleicoes.adapters.streaming_transfer import StreamingFileTransfer  # noqa: E402
from eleicoes.domain.calibracao_turnos import calibrar, como_json  # noqa: E402
from eleicoes.domain.layout import locate  # noqa: E402
from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS  # noqa: E402
from eleicoes.domain.values import RemoteZip  # noqa: E402

_ANO: Final = 2022
_APOIADO: Final = 22
_OUTRO: Final = 13
_PASTA: Final = RAIZ / "downloads" / "2022-calibracao"
_SAIDA: Final = RAIZ / "dados" / "calibracao_turnos_2022.json"


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    pasta: Path = args.pasta
    conjuntos = (VOTOS_POR_CANDIDATO, DETALHE_DA_VOTACAO)
    zips = tuple(RemoteZip(url_munzona(nome, _ANO), f"{nome}_{_ANO}.zip") for nome in conjuntos)
    transfer = StreamingFileTransfer(RequestsHttpClient())
    for remoto in zips:
        transfer.transfer(remoto, pasta)
    votos, detalhe = (pasta / locate(remoto.filename).relative_path for remoto in zips)
    turnos = ler_presidente_munzona(votos, detalhe)
    if set(turnos) != {1, 2}:
        print("Os zips não trazem os dois turnos de presidente.", file=sys.stderr)
        return EXIT_FAILURE
    calibracao = calibrar(turnos[1], turnos[2], _APOIADO, _OUTRO)
    texto = json.dumps(
        como_json(calibracao, _ANO, [remoto.url for remoto in zips]), ensure_ascii=False, indent=2
    )
    args.saida.write_text(texto + "\n", encoding="utf-8")
    print(f"Calibração gravada em {args.saida}.")
    return EXIT_SUCCESS


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Calibra os limiares do 1º × 2º turno com a eleição de 2022."
    )
    parser.add_argument("--pasta", type=Path, default=_PASTA, help="Pasta dos zips do TSE.")
    parser.add_argument("--saida", type=Path, default=_SAIDA, help="JSON gerado.")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
