"""Mostra de onde vieram os votos novos dos finalistas no 2º turno de presidente.

Uso, na raiz do projeto:

    uv run python scripts/relatorio_origem_votos.py --ano 2026

Lê os lugares municipais já gravados pelo relatório do mapa (os dois turnos) e o
comparecimento do boletim, uma consulta por UF e turno. O navegador abre o HTML; o CSV
fica ao lado. Para só gravar os arquivos:

    uv run python scripts/relatorio_origem_votos.py --ano 2026 --sem-navegador
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from eleicoes.use_cases.apresentar_origem_votos import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
