"""Estima a classe do governador a partir do perfil do presidente.

Uso, na raiz do projeto:

    uv run python scripts/relatorio_classe_governador.py --ano 2026 --turno 1

O navegador abre o HTML. Para só gravar o arquivo:

    uv run python scripts/relatorio_classe_governador.py --ano 2026 --turno 1 --sem-navegador
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from eleicoes.use_cases.apresentar_classe_governador import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
