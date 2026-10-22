import re
from pathlib import Path

from eleicoes.domain.partido_equivalencia import (
    TABELA_2024_2026,
    VERSAO_EQUIVALENCIA,
    Correspondencia,
    equivalente_2026,
)

_PARTIDOS_TS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "partidos.ts"
_LINHA = re.compile(r'^\s*(\d+): "([^"]+)",\s*$')


def test_same_number_and_sigla_is_mesmo() -> None:
    found = equivalente_2026(22, "PL")
    assert found.correspondencia is Correspondencia.MESMO
    assert (found.numero_2026, found.sigla_2026) == (22, "PL")


def test_pmb_became_democrata() -> None:
    found = equivalente_2026(35, "PMB")
    assert found.correspondencia is Correspondencia.RENOMEADO
    assert (found.numero_2026, found.sigla_2026) == (35, "DEMOCRATA")
    assert "2/12/2025" in found.nota


def test_pc_do_b_is_only_a_spelling_change() -> None:
    found = equivalente_2026(65, "PC do B")
    assert found.correspondencia is Correspondencia.GRAFIA
    assert found.sigla_2026 == "PCdoB"


def test_unexpected_sigla_is_divergente_but_keeps_the_number() -> None:
    found = equivalente_2026(22, "XYZ")
    assert found.correspondencia is Correspondencia.DIVERGENTE
    assert found.numero_2026 == 22


def test_unknown_number_has_no_counterpart() -> None:
    found = equivalente_2026(14, "PTB")
    assert found.correspondencia is Correspondencia.SEM_CORRESPONDENCIA
    assert found.numero_2026 is None
    assert found.sigla_2026 is None


def test_table_has_the_29_parties_of_2024_and_a_version() -> None:
    assert len(TABELA_2024_2026) == 29
    assert VERSAO_EQUIVALENCIA == "2026-10-22"


def test_2026_siglas_match_the_frontend_registry() -> None:
    registry: dict[int, str] = {}
    for line in _PARTIDOS_TS.read_text(encoding="utf-8").splitlines():
        found = _LINHA.match(line)
        if found is not None:
            registry[int(found.group(1))] = found.group(2)
    for item in TABELA_2024_2026:
        assert item.numero_2026 is not None
        assert registry[item.numero_2026] == item.sigla_2026
