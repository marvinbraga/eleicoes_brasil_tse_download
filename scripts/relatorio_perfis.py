"""Agrupa os municípios pelo perfil de voto.

Uso, na raiz do projeto:

    uv run python scripts/relatorio_perfis.py --ano 2026 --turno 1 --cargo presidente

O navegador abre o HTML. Para só gravar o arquivo:

    uv run python scripts/relatorio_perfis.py --ano 2026 --turno 1 \\
        --cargo presidente --sem-navegador
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from eleicoes.use_cases.apresentar_perfis import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
