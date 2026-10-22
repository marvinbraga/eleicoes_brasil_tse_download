import pytest

from eleicoes.domain.errors import InvalidGenerationError, InvalidMunicipalYearError
from eleicoes.domain.municipal_contract import (
    CONSULTA_CAND,
    CONSULTA_VAGAS,
    DETALHE_VOTACAO_MUNZONA,
    MUNICIPAL_UFS,
    expected_members,
    generation_from_csv,
    municipal_archives,
    municipal_member,
    require_municipal_year,
)
from eleicoes.domain.values import ElectionYear


def test_member_by_uf_selects_the_contract_and_the_uf() -> None:
    found = municipal_member("consulta_cand_2024_MG.csv", 2024)
    assert found is not None
    assert found.contract is CONSULTA_CAND
    assert found.uf == "MG"
    vagas = municipal_member("consulta_vagas_2024_AC.csv", 2024)
    assert vagas is not None and vagas.contract is CONSULTA_VAGAS
    detalhe = municipal_member("detalhe_votacao_munzona_2024_SP.csv", 2024)
    assert detalhe is not None and detalhe.contract is DETALHE_VOTACAO_MUNZONA


@pytest.mark.parametrize(
    "name",
    [
        "consulta_cand_2024_BRASIL.csv",
        "leiame.pdf",
        "consulta_cand_2020_MG.csv",
        "consulta_cand_2024_DF.csv",
        "consulta_cand_2024_ZZ.csv",
        "votacao_candidato_munzona_2024_MG.csv",
    ],
)
def test_national_readme_other_year_and_non_municipal_uf_are_ignored(name: str) -> None:
    assert municipal_member(name, 2024) is None


def test_26_municipal_ufs() -> None:
    assert len(MUNICIPAL_UFS) == 26
    assert "DF" not in MUNICIPAL_UFS and "ZZ" not in MUNICIPAL_UFS


def test_contract_headers_have_the_published_widths() -> None:
    assert len(CONSULTA_CAND.columns) == 50
    assert len(DETALHE_VOTACAO_MUNZONA.columns) == 47
    assert len(CONSULTA_VAGAS.columns) == 15
    assert CONSULTA_CAND.columns[-2:] == ("CD_SIT_TOT_TURNO", "DS_SIT_TOT_TURNO")


def test_archives_of_2024_come_from_two_packages() -> None:
    archives = municipal_archives(ElectionYear(2024))
    assert [(item.package, item.filename) for item in archives] == [
        ("candidatos-2024", "consulta_cand_2024.zip"),
        ("candidatos-2024", "consulta_vagas_2024.zip"),
        ("resultados-2024", "detalhe_votacao_munzona_2024.zip"),
    ]


def test_general_election_year_is_rejected() -> None:
    with pytest.raises(InvalidMunicipalYearError):
        require_municipal_year(ElectionYear(2026))


def test_generation_comes_from_the_first_row() -> None:
    payload = '"DT_GERACAO";"HH_GERACAO";"X"\r\n"22/10/2026";"02:17:07";"1"\r\n'.encode("latin-1")
    assert generation_from_csv("m.csv", payload) == "221020260217"


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b'"DT_GERACAO";"HH_GERACAO"\r\n',
        b'"A";"B"\r\n"22/10/2026";"02:17:07"\r\n',
        b'"DT_GERACAO";"HH_GERACAO"\r\n"99/99/2026";"02:17:07"\r\n',
    ],
)
def test_generation_without_a_valid_first_row_fails(payload: bytes) -> None:
    with pytest.raises(InvalidGenerationError):
        generation_from_csv("m.csv", payload)


def test_expected_members_are_three_conjuntos_by_26_ufs() -> None:
    names = expected_members(2024)
    assert len(names) == 78 == len(set(names))
    assert names[0] == "consulta_cand_2024_AC.csv"
    assert all(municipal_member(name, 2024) is not None for name in names)
