"""Pinta o partido líder de presidente ou de governador.

Uso, na raiz do projeto:

    uv run python scripts/relatorio_mapa.py --ano 2026 --turno 1 --cargo presidente

O navegador abre o HTML. Para só gravar o arquivo:

    uv run python scripts/relatorio_mapa.py --ano 2026 --turno 1 --cargo governador --sem-navegador
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from eleicoes.use_cases.apresentar_mapa import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
