"""Compara o 1º e o 2º turno de presidente por região e porte do município.

Uso, na raiz do projeto:

    uv run python scripts/relatorio_regioes_porte.py --ano 2026

O navegador abre o HTML. Para só gravar o arquivo:

    uv run python scripts/relatorio_regioes_porte.py --ano 2026 --sem-navegador
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from eleicoes.use_cases.apresentar_regioes_porte import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
