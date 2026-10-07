import pytest
from tests.boletim_fakes import bulletin, nominal_line

from eleicoes.domain.boletim import Boletim, BoletimImportReport
from eleicoes.domain.errors import InvalidBoletimContentError
from eleicoes.domain.report import EXIT_NOT_PUBLISHED, EXIT_SUCCESS


def test_vote_line_accepts_legenda_consulta_and_cargo_sem_candidato() -> None:
    nominal_line(tipo_voto="legenda", partido=13, numero=13)
    nominal_line(
        tipo_cargo="consulta",
        cargo="25",
        tipo_voto="cargoSemCandidato",
        partido=None,
        numero=None,
    )
    stored = bulletin()
    assert stored.total_for(6257, "presidente") == 1
    assert stored.lines_for(1, "presidente") == ()


def test_blank_and_null_votes_reject_an_identification() -> None:
    with pytest.raises(InvalidBoletimContentError) as caught:
        nominal_line(tipo_voto="branco", partido=13, numero=None)
    assert caught.value.field == "identificacao"


def test_nominal_vote_requires_partido_and_numero() -> None:
    with pytest.raises(InvalidBoletimContentError) as caught:
        nominal_line(partido=None, numero=None)
    assert caught.value.field == "identificacao"


def test_cargo_must_be_constitutional_or_a_free_number() -> None:
    nominal_line(tipo_cargo="consulta", cargo="99")
    with pytest.raises(InvalidBoletimContentError) as caught:
        nominal_line(cargo="24")
    assert caught.value.field == "cargo"
    with pytest.raises(InvalidBoletimContentError) as padded:
        nominal_line(tipo_cargo="consulta", cargo="025")
    assert padded.value.field == "cargo"


def test_negative_quantity_and_bool_are_rejected() -> None:
    with pytest.raises(InvalidBoletimContentError) as caught:
        nominal_line(quantidade=-1)
    assert caught.value.field == "quantidade"
    with pytest.raises(InvalidBoletimContentError) as boolean:
        nominal_line(quantidade=True)
    assert boolean.value.field == "quantidade"


def test_section_path_phase_and_stamp_are_always_valid() -> None:
    with pytest.raises(InvalidBoletimContentError) as path:
        bulletin(arquivo="../segredo-bu.dat")
    assert path.value.field == "arquivo"
    with pytest.raises(InvalidBoletimContentError) as fase:
        Boletim(**_fields(fase="simulado"))
    assert fase.value.field == "fase"
    with pytest.raises(InvalidBoletimContentError) as stamp:
        Boletim(**_fields(data_hora_emissao="2026-10-04"))
    assert stamp.value.field == "data_hora_emissao"
    with pytest.raises(InvalidBoletimContentError) as section:
        Boletim(**_fields(municipio=0))
    assert section.value.field == "municipio"


def test_inconsistent_lines_are_rejected() -> None:
    first = nominal_line()
    other_total = nominal_line(eleitores_aptos=10, tipo_voto="nulo", partido=None, numero=None)
    with pytest.raises(InvalidBoletimContentError) as election:
        bulletin(votos=(first, other_total))
    assert election.value.field == "eleicao"
    other_order = nominal_line(ordem_impressao=6, tipo_voto="nulo", partido=None, numero=None)
    with pytest.raises(InvalidBoletimContentError) as cargo:
        bulletin(votos=(first, other_order))
    assert cargo.value.field == "cargo"


def test_report_without_bulletins_is_not_found() -> None:
    assert BoletimImportReport(0, 0).exit_code == EXIT_NOT_PUBLISHED
    assert BoletimImportReport(1, 0).exit_code == EXIT_SUCCESS
    assert BoletimImportReport(0, 0).ausentes == ()
    assert BoletimImportReport(1, 0, ("imgbu.dat",)).exit_code == EXIT_SUCCESS


def _fields(**overrides: object) -> dict[str, object]:
    source = bulletin()
    values: dict[str, object] = {
        "arquivo": source.arquivo,
        "fase": source.fase,
        "municipio": source.municipio,
        "zona": source.zona,
        "local": source.local,
        "secao": source.secao,
        "data_hora_emissao": source.data_hora_emissao,
        "versao_urna": source.versao_urna,
        "numero_interno_urna": source.numero_interno_urna,
        "data_hora_carga": source.data_hora_carga,
        "codigo_carga": source.codigo_carga,
        "codigo_midia": source.codigo_midia,
        "eleitores_computados": source.eleitores_computados,
        "indicador_habilitacao": source.indicador_habilitacao,
        "qtd_biometria": source.qtd_biometria,
        "qtd_manual": source.qtd_manual,
        "votos": source.votos,
    }
    values.update(overrides)
    return values
