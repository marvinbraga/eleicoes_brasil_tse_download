"""Grava os votos por candidato que a simulação de cadeiras usa.

Uso, na raiz do projeto:

    uv run python scripts/relatorio_cadeiras.py

Soma os boletins uma vez por cargo (governador, senador, deputadoFederal,
deputadoEstadual e deputadoDistrital) e grava em analise.relatorio_cadeiras_voto.
Um cargo já gravado não é somado de novo. Para refazer:

    uv run python scripts/relatorio_cadeiras.py --atualizar
    uv run python scripts/relatorio_cadeiras.py --cargo deputadoFederal --atualizar

As cadeiras não são gravadas: a API as calcula a partir desses votos.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from eleicoes.use_cases.gravar_cadeiras import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
