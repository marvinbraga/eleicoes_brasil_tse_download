"""Mostra como cada estado votou nos dois mais votados para presidente.

Uso, na raiz do projeto:

    uv run python scripts/relatorio_estados.py --ano 2026 --turno 2

Lê os votos municipais já gravados no banco, as marcas dos partidos em
downloads/malha e o índice de download das urnas. O navegador abre o HTML.
Para só gravar o arquivo:

    uv run python scripts/relatorio_estados.py --ano 2026 --turno 1 --sem-navegador
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from eleicoes.use_cases.apresentar_votos_por_estado import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
