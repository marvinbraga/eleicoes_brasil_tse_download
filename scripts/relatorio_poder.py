"""Apresenta o poder do partido por município, estado, região e país.

Uso, na raiz do projeto:

    uv run python scripts/relatorio_poder.py

O navegador abre o HTML. Para só gravar o arquivo:

    uv run python scripts/relatorio_poder.py --sem-navegador

O banco guarda as grades. O HTML é montado em cada apresentação.
Na vez seguinte o comando não agrega os boletins de novo. Para
recalcular as grades e substituir as linhas guardadas:

    uv run python scripts/relatorio_poder.py --atualizar
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from eleicoes.use_cases.apresentar_grade import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
