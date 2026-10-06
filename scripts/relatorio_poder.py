"""Apresenta o poder do partido por município, estado, região e país.

Uso, na raiz do projeto:

    uv run python scripts/relatorio_poder.py

O navegador abre o HTML. Para só gravar o arquivo:

    uv run python scripts/relatorio_poder.py --sem-navegador
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from eleicoes.use_cases.apresentar_grade import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
