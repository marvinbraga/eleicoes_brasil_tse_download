"""Compara o 1º e o 2º turno de presidente seção por seção.

Uso, na raiz do projeto:

    uv run python scripts/relatorio_secoes_turnos.py --ano 2026

O navegador abre o HTML; o CSV fica ao lado. Para só gravar os arquivos:

    uv run python scripts/relatorio_secoes_turnos.py --ano 2026 --sem-navegador
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from eleicoes.use_cases.apresentar_secoes_turnos import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
