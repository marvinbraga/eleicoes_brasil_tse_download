"""Confere a assinatura digital (vota.vsc) de cada seção baixada.

Uso, na raiz do projeto:

    uv run python scripts/verificar_assinaturas.py --ano 2026 --turno 2
    uv run python scripts/verificar_assinaturas.py --ano 2026 --turno 1 --uf AC --processos 2

Grava relatorios/assinaturas-urnas-{ano}-turno-{turno}.html e o CSV com todas as seções.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from eleicoes.use_cases.verificar_assinaturas import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
