"""Confere boletim de urna × registro digital do voto (RDV) × log de cada seção baixada.

Uso, na raiz do projeto:

    uv run python scripts/verificar_urnas.py --ano 2026 --turno 2
    uv run python scripts/verificar_urnas.py --ano 2026 --turno 2 --uf AC --uf AL

Grava relatorios/integridade-urnas-{ano}-turno-{turno}.html e o CSV com todas as seções.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from eleicoes.use_cases.verificar_urnas import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
