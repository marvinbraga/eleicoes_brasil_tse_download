"""Cruza o partido do governador com o 1º e o 2º da presidência.

Uso, na raiz do projeto:

    uv run python scripts/relatorio_presidente_governador.py --ano 2026 --turno 1

O navegador abre o HTML. Para só gravar o arquivo:

    uv run python scripts/relatorio_presidente_governador.py --ano 2026 --turno 1 --sem-navegador

O banco guarda os votos municipais. O HTML é montado em cada apresentação.
Na vez seguinte o comando não lê os boletins de novo. Para recalcular:

    uv run python scripts/relatorio_presidente_governador.py --ano 2026 --turno 1 --atualizar
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from eleicoes.use_cases.apresentar_presidente_governador import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
