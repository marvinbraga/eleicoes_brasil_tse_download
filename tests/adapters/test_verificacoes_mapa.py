"""Seções e verificação das urnas viram contagens por município, na chave da malha."""

from pathlib import Path

from eleicoes.adapters.verificacoes_mapa import (
    codigo_no_mapa,
    integridade_por_municipio,
    ler_verificacoes,
    secoes_por_municipio,
)
from eleicoes.domain.mapa import PonteTseIbge

_PONTE = PonteTseIbge(municipio_por_tse={"01007": "1200138"}, uf_por_sigla={"AC": "12"})


def test_code_goes_through_the_bridge_and_abroad_keeps_tse_code() -> None:
    assert codigo_no_mapa("AC", "1007", _PONTE) == "1200138"
    assert codigo_no_mapa("ZZ", "29539", _PONTE) == "29539"
    assert codigo_no_mapa("AC", "9999", _PONTE) is None


def test_sections_count_evaluated_and_out_of_range_per_scenario() -> None:
    linhas = [
        {"uf": "AC", "municipio": "1007", "classe_todosa": "fora_a", "classe_dividido": "dentro"},
        {"uf": "AC", "municipio": "1007", "classe_todosa": "fora_b", "classe_dividido": "fora_a"},
        {"uf": "AC", "municipio": "1007", "classe_todosa": "sem_base", "classe_dividido": ""},
        {"uf": "AC", "municipio": "9999", "classe_todosa": "fora_a", "classe_dividido": "fora_a"},
    ]

    found = secoes_por_municipio(linhas, _PONTE)

    assert found == {"1200138": {"comZ": 2, "fora": {"todosa": 2, "dividido": 1}}}


def test_integrity_counts_sections_by_situation() -> None:
    linhas = [
        {"uf": "AC", "municipio": "1007", "situacao": "confere"},
        {"uf": "AC", "municipio": "1007", "situacao": "confere"},
        {"uf": "AC", "municipio": "1007", "situacao": "sem_log"},
        {"uf": "AC", "municipio": "1007", "situacao": "estranha"},
        {"uf": "AC", "municipio": "9999", "situacao": "confere"},
    ]

    assert integridade_por_municipio(linhas, _PONTE) == {"1200138": [2, 0, 0, 1, 0]}


def test_reading_returns_none_without_files(tmp_path: Path) -> None:
    assert ler_verificacoes(tmp_path / "a.csv", tmp_path / "b.csv", _PONTE) is None


def test_reading_keeps_each_part_on_its_own(tmp_path: Path) -> None:
    integridade = tmp_path / "integridade.csv"
    integridade.write_text(
        "uf,municipio,zona,secao,urna,situacao\nAC,1007,9,1,2468149,diverge\n", encoding="utf-8"
    )

    found = ler_verificacoes(tmp_path / "secoes.csv", integridade, _PONTE)

    assert found is not None
    assert "secoes" not in found
    assert found["integridade"] == {"1200138": [0, 1, 0, 0, 0]}
    assert found["situacoes"] == ["confere", "diverge", "sem_rdv", "sem_log", "ilegivel"]
    assert isinstance(found["integridadeEm"], str)


def test_reading_sections_file_with_bom(tmp_path: Path) -> None:
    secoes = tmp_path / "secoes.csv"
    secoes.write_text("uf,municipio,classe_todosa\nAC,1007,fora_a\n", encoding="utf-8-sig")

    found = ler_verificacoes(secoes, tmp_path / "integridade.csv", _PONTE)

    assert found is not None
    assert found["secoes"] == {"1200138": {"comZ": 1, "fora": {"todosa": 1}}}
    assert "integridade" not in found
