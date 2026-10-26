"""Estima pelos dados para onde foram os votos do 1º turno de presidente no 2º.

Uso, na raiz do projeto:

    uv run python scripts/estimar_transferencia.py --ano 2026

Só lê o banco. Estima cada UF que já tem o 2º turno importado e imprime as
taxas de transferência com intervalo de 90% por bootstrap. Para outro nível
ou mais reamostras:

    uv run python scripts/estimar_transferencia.py --ano 2026 --nivel 0.95 --reamostras 2000
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from eleicoes.use_cases.estimar_transferencia import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
