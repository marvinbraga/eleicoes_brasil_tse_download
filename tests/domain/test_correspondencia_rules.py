"""Regras de correspondência: status, nomes, mudanças e indícios."""

from datetime import datetime

import pytest

from eleicoes.domain.correspondencia import (
    Contingencia,
    Gravidade,
    Indicio,
    MapaDeIndicios,
    MudancaGeracao,
    ProjecaoContingencia,
    ProjecaoSecao,
    Referencia,
    ResumoUf,
    Secao,
    StatusCorrespondencia,
    modified_z,
    nomes_equivalentes,
)
from eleicoes.domain.errors import (
    InvalidCorrespondenceRecordError,
    InvalidUfError,
    UnknownCorrespondenceStatusError,
)

_WHEN = datetime(2026, 10, 4, 12, 59)


def test_status_accepts_the_official_codes() -> None:
    assert StatusCorrespondencia.from_code("N") is StatusCorrespondencia.NAO_ALTERADA
    assert StatusCorrespondencia.from_code("S") is StatusCorrespondencia.ALTERADA
    assert StatusCorrespondencia.from_code("*") is StatusCorrespondencia.NOVA


@pytest.mark.parametrize("code", ["", "X", "s", "n"])
def test_status_rejects_unknown_codes(code: str) -> None:
    with pytest.raises(UnknownCorrespondenceStatusError):
        StatusCorrespondencia.from_code(code)


def test_names_ignore_case_and_accents() -> None:
    assert nomes_equivalentes("Sao Paulo", "SÃO PAULO") is True
    assert nomes_equivalentes("acao", "AÇÃO") is True
    assert nomes_equivalentes("Rio Branco", "RIO BRANCO") is True
    assert nomes_equivalentes("Rio Branco", "Brasileia") is False


def test_section_normalizes_the_uf_and_keeps_the_municipality_code() -> None:
    secao = _secao(uf="ac")
    assert secao.uf == "AC"
    assert secao.codigo_municipio == "01392"


def test_records_reject_an_invalid_uf_or_a_negative_count() -> None:
    assert _contingencia().uf == "AC"
    assert ResumoUf("ac", 1, 1, 1, 1, 0, 0, 0, 0).uf == "AC"
    with pytest.raises(InvalidUfError):
        _secao(uf="XX")
    with pytest.raises(InvalidCorrespondenceRecordError):
        _secao(zona=-1)
    with pytest.raises(InvalidCorrespondenceRecordError):
        _secao(zona=True)  # type: ignore[arg-type]
    with pytest.raises(InvalidCorrespondenceRecordError):
        ResumoUf("AC", 1, 1, 1, 1, 0, 0, 0, -1)


def test_generation_change_lists_only_the_fields_that_differ() -> None:
    change = _change(flashcard_atual="BBBBBBBB", maquina_atual="OUTRA")
    assert change.campos_alterados == ("urna", "flashcard", "maquina")


def test_generation_change_rejects_an_empty_difference() -> None:
    with pytest.raises(ValueError):
        _change(urna_atual="1")


def test_modified_z_is_zero_on_the_median_and_infinite_when_mad_is_zero() -> None:
    assert modified_z(1.0, 1.0, 0.0) == 0.0
    assert modified_z(2.0, 1.0, 0.0) == float("inf")
    assert modified_z(2.0, 1.0, 2.0) == pytest.approx(0.6745 * 0.5)


def test_same_cargo_on_two_sections_is_one_high_finding() -> None:
    secoes = (
        _projecao(secao=1, carga="CARGA-9", urna="1"),
        _projecao(secao=2, carga="CARGA-9", urna="2"),
    )
    found = MapaDeIndicios().avaliar(secoes, ())
    assert len(found) == 1
    indicio = found[0]
    assert indicio.codigo == "CARGA_COMPARTILHADA"
    assert indicio.gravidade is Gravidade.ALTA
    assert indicio.descricao == "O código de carga CARGA-9 está previsto em 2 seções."
    assert indicio.uf == "AC"
    assert indicio.municipio == "RIO BRANCO"
    assert len(indicio.referencias) == 2


def test_same_cargo_across_municipalities_has_no_single_place() -> None:
    secoes = (
        _projecao(secao=1, carga="CARGA-9", codigo="00001", municipio="A"),
        _projecao(secao=2, carga="CARGA-9", codigo="00002", municipio="B", uf="SP"),
    )
    found = MapaDeIndicios().avaliar(secoes, ())
    assert found[0].uf == ""
    assert found[0].municipio == ""


def test_sentinel_cargo_or_urn_repeated_is_not_a_finding() -> None:
    secoes = [
        _projecao(secao=index, carga=cargo, urna=str(index))
        for index, cargo in enumerate(("#NULO", "#NULO", "#NE", "#NE", "", "", "-1", "-1"), start=1)
    ]
    secoes.extend(
        (
            _projecao(secao=20, carga="U1", urna="#NULO", zona=3),
            _projecao(secao=21, carga="U2", urna="#NULO", zona=3),
            _projecao(secao=22, carga="U3", urna="-3", zona=3),
            _projecao(secao=23, carga="U4", urna="  #NE  ", zona=3),
        )
    )
    assert MapaDeIndicios().avaliar(secoes, ()) == ()


def test_same_urn_in_one_zone_is_a_high_finding() -> None:
    secoes = (
        _projecao(secao=1, urna="2269941", carga="A", zona=9),
        _projecao(secao=2, urna="2269941", carga="B", zona=9),
    )
    found = MapaDeIndicios().avaliar(secoes, ())
    assert len(found) == 1
    assert found[0].codigo == "URNA_COMPARTILHADA_NA_ZONA"
    assert found[0].gravidade is Gravidade.ALTA
    assert found[0].descricao == (
        "A urna 2269941 está prevista em 2 seções da zona 9 de RIO BRANCO."
    )


def test_same_urn_in_different_zones_is_normal() -> None:
    secoes = (
        _projecao(secao=1, urna="2269941", carga="A", zona=1),
        _projecao(secao=1, urna="2269941", carga="B", zona=2),
    )
    assert MapaDeIndicios().avaliar(secoes, ()) == ()


def test_repeated_flashcard_with_different_cargo_is_normal() -> None:
    secoes = (
        _projecao(secao=1, carga="A", urna="1", flashcard="FA10805F"),
        _projecao(secao=2, carga="B", urna="2", flashcard="FA10805F"),
    )
    assert MapaDeIndicios().avaliar(secoes, ()) == ()


def test_altered_status_alone_is_not_a_finding() -> None:
    secoes = (
        _projecao(secao=1, status=StatusCorrespondencia.ALTERADA, carga="A", urna="1"),
        _projecao(secao=2, status=StatusCorrespondencia.ALTERADA, carga="B", urna="2"),
    )
    assert MapaDeIndicios().avaliar(secoes, ()) == ()


def test_alteration_rate_uses_the_modified_z_rule() -> None:
    plan = (
        ("M00", 0),
        ("M01", 0),
        ("M02", 1),
        ("M03", 1),
        ("M04", 2),
        ("M05", 2),
        ("M06", 2),
        ("NORMAL", 3),
        ("OUTLIER", 8),
    )
    secoes = _sections_for(plan, size=20)
    secoes.extend(_sections_for((("TINY", 9),), size=9, zona=99))
    rates = [events / 20 for _codigo, events in plan if events >= 1]
    center = _median(rates)
    spread = _median([abs(rate - center) for rate in rates])
    outlier_z = modified_z(8 / 20, center, spread)
    neighbor_z = modified_z(3 / 20, center, spread)
    assert outlier_z >= 3.5
    assert neighbor_z < 3.5

    found = MapaDeIndicios().avaliar(secoes, ())
    assert [item.codigo for item in found] == ["TAXA_ALTERACAO_ATIPICA"]
    indicio = found[0]
    assert indicio.gravidade is Gravidade.MEDIA
    assert indicio.municipio == "OUTLIER"
    assert indicio.descricao == (
        "OUTLIER (AC) tem taxa de correspondência alterada fora do padrão dos municípios: "
        f"{8 / 20:.2%} em 20 seções (z = {outlier_z:.1f})."
    )
    assert indicio.medida == f"8 seções alteradas em 20; z = {outlier_z:.1f}."
    assert "NORMAL" not in indicio.descricao


def test_one_altered_municipality_against_zeros_is_not_an_outlier() -> None:
    plan = tuple((f"Z{index:02d}", 0) for index in range(10)) + (("PAR", 2),)
    assert MapaDeIndicios().avaliar(_sections_for(plan, size=10), ()) == ()


def test_equal_positive_rates_are_not_outliers() -> None:
    plan = (("A", 2), ("B", 2), ("C", 2))
    assert MapaDeIndicios().avaliar(_sections_for(plan, size=10), ()) == ()


def test_mild_even_population_is_not_an_alteration_outlier() -> None:
    plan = (("CALMO", 0), ("LEVE", 1))
    assert MapaDeIndicios().avaliar(_sections_for(plan, size=10), ()) == ()


def test_machine_share_needs_four_of_at_least_five_and_half_the_uf() -> None:
    secoes: list[ProjecaoSecao] = []
    secoes.extend(_altered_by_machine("AC", "MAQ-A", 4))
    secoes.extend(_altered_by_machine("AC", "MAQ-B", 1))
    secoes.extend(_altered_by_machine("SP", "MAQ-A", 4))
    secoes.extend(_altered_by_machine("SP", "MAQ-B", 1))
    secoes.extend(_altered_by_machine("RJ", "MAQ-A", 2))
    secoes.extend(_altered_by_machine("RJ", "MAQ-B", 3))
    secoes.extend(_altered_by_machine("MG", "MAQ-A", 4))
    secoes.extend(_altered_by_machine("MG", "MAQ-B", 3))
    secoes.extend(_altered_by_machine("MG", "MAQ-C", 3))
    secoes.extend(_altered_by_machine("BA", "", 4))
    secoes.extend(_altered_by_machine("BA", "MAQ-A", 1))
    secoes.extend(_altered_by_machine("PR", "MAQ-A", 4))

    found = MapaDeIndicios().avaliar(secoes, ())
    assert [item.codigo for item in found] == [
        "MAQUINA_CONCENTRA_ALTERACOES",
        "MAQUINA_CONCENTRA_ALTERACOES",
    ]
    assert [item.uf for item in found] == ["AC", "SP"]
    assert found[0].gravidade is Gravidade.MEDIA
    assert found[0].descricao == (
        "Em AC, a máquina MAQ-A gerou 4 das 5 correspondências alteradas."
    )
    assert found[0].municipio == ""


def test_new_section_is_its_own_finding() -> None:
    secoes = (
        _projecao(
            secao=10,
            zona=7,
            status=StatusCorrespondencia.NOVA,
            carga="SOLO",
            urna="SOLO",
        ),
    )
    found = MapaDeIndicios().avaliar(secoes, ())
    assert len(found) == 1
    assert found[0].codigo == "SECAO_NOVA"
    assert found[0].gravidade is Gravidade.MEDIA
    assert found[0].descricao == (
        "A seção 10 de RIO BRANCO (AC), zona 7, entrou como correspondência nova entre as gerações."
    )
    assert found[0].referencias[0].secao == 10


def test_contingency_outlier_uses_the_modified_z_rule() -> None:
    plan = (
        ("C00", 0),
        ("C01", 0),
        ("C02", 1),
        ("C03", 1),
        ("C04", 2),
        ("C05", 2),
        ("C06", 2),
        ("CALMA", 3),
        ("PICO", 8),
    )
    rows = _contingencies_for(plan, size=20)
    rates = [events / 20 for _codigo, events in plan if events >= 1]
    center = _median(rates)
    spread = _median([abs(rate - center) for rate in rates])
    outlier_z = modified_z(8 / 20, center, spread)
    assert outlier_z >= 3.5
    found = MapaDeIndicios().avaliar((), rows)
    assert [item.codigo for item in found] == ["CONTINGENCIA_NOVA_CONCENTRADA"]
    assert found[0].gravidade is Gravidade.BAIXA
    assert found[0].descricao == (
        f"PICO (AC) concentrou 8 urnas de contingência novas em 20 urnas (z = {outlier_z:.1f})."
    )


def test_one_new_contingency_urn_in_a_large_population_is_not_a_finding() -> None:
    plan = tuple((f"N{index:02d}", 0) for index in range(10)) + (("UNICA", 1),)
    assert MapaDeIndicios().avaliar((), _contingencies_for(plan, size=20)) == ()


def test_findings_are_ordered_by_severity_then_code_then_place() -> None:
    secoes = [
        _projecao(secao=1, carga="MESMA", urna="1"),
        _projecao(secao=2, carga="MESMA", urna="2"),
        _projecao(secao=3, carga="NOVA-1", urna="3", status=StatusCorrespondencia.NOVA),
    ]
    secoes.extend(_altered_by_machine("AC", "MAQ-A", 4))
    secoes.extend(_altered_by_machine("AC", "MAQ-B", 1))
    contingencias = _contingencies_for(
        (
            ("C00", 0),
            ("C01", 1),
            ("C02", 1),
            ("C03", 2),
            ("C04", 2),
            ("C05", 2),
            ("CALMA", 3),
            ("PICO", 8),
        ),
        size=20,
    )
    found = MapaDeIndicios().avaliar(secoes, contingencias)
    assert [item.gravidade for item in found] == [
        Gravidade.ALTA,
        Gravidade.MEDIA,
        Gravidade.MEDIA,
        Gravidade.BAIXA,
    ]
    assert [item.codigo for item in found] == [
        "CARGA_COMPARTILHADA",
        "MAQUINA_CONCENTRA_ALTERACOES",
        "SECAO_NOVA",
        "CONTINGENCIA_NOVA_CONCENTRADA",
    ]


def test_indicio_requires_text_and_accepts_an_empty_place() -> None:
    indicio = Indicio(
        codigo="SECAO_NOVA",
        descricao="texto",
        gravidade=Gravidade.MEDIA,
        uf="",
        municipio="",
        medida="1",
        referencias=(),
    )
    assert indicio.uf == ""
    with pytest.raises(InvalidCorrespondenceRecordError):
        Indicio(
            codigo=" ",
            descricao="texto",
            gravidade=Gravidade.MEDIA,
            uf="",
            municipio="",
            medida="1",
            referencias=(),
        )


def test_contingency_reference_has_no_section() -> None:
    item = ProjecaoContingencia(
        uf="ac",
        codigo_municipio="01392",
        municipio="RIO BRANCO",
        zona=1,
        urna="55",
        status=StatusCorrespondencia.NOVA,
    )
    assert item.uf == "AC"
    referencia = Referencia(
        uf="AC",
        codigo_municipio="01392",
        municipio="RIO BRANCO",
        zona=1,
        secao=None,
        urna="55",
    )
    assert referencia.secao is None
    assert referencia.urna == "55"


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    count = len(ordered)
    middle = count // 2
    if count % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _sections_for(
    plan: tuple[tuple[str, int], ...],
    size: int,
    zona: int = 1,
) -> list[ProjecaoSecao]:
    rows: list[ProjecaoSecao] = []
    for codigo, events in plan:
        for number in range(1, size + 1):
            status = (
                StatusCorrespondencia.ALTERADA
                if number <= events
                else StatusCorrespondencia.NAO_ALTERADA
            )
            rows.append(
                _projecao(
                    uf="AC",
                    codigo=codigo,
                    municipio=codigo,
                    zona=zona,
                    secao=number,
                    urna=f"{codigo}-{number}",
                    carga=f"C-{codigo}-{number}",
                    flashcard=f"F{number:07d}",
                    status=status,
                    maquina=f"M-{codigo}-{number}",
                )
            )
    return rows


def _contingencies_for(
    plan: tuple[tuple[str, int], ...],
    size: int,
) -> list[ProjecaoContingencia]:
    rows: list[ProjecaoContingencia] = []
    for codigo, events in plan:
        for number in range(1, size + 1):
            status = (
                StatusCorrespondencia.NOVA
                if number <= events
                else StatusCorrespondencia.NAO_ALTERADA
            )
            rows.append(
                ProjecaoContingencia(
                    uf="AC",
                    codigo_municipio=codigo,
                    municipio=codigo,
                    zona=1,
                    urna=f"{codigo}-{number}",
                    status=status,
                )
            )
    return rows


def _altered_by_machine(uf: str, machine: str, count: int) -> list[ProjecaoSecao]:
    return [
        _projecao(
            uf=uf,
            codigo=uf,
            municipio=uf,
            zona=1,
            secao=index + 1,
            urna=f"{uf}-{machine}-{index}",
            carga=f"C-{uf}-{machine}-{index}",
            status=StatusCorrespondencia.ALTERADA,
            maquina=machine,
        )
        for index in range(count)
    ]


def _projecao(
    *,
    uf: str = "AC",
    codigo: str = "01392",
    municipio: str = "RIO BRANCO",
    zona: int = 1,
    secao: int = 1,
    urna: str = "100",
    carga: str = "CARGA",
    flashcard: str = "AABBCCDD",
    status: StatusCorrespondencia = StatusCorrespondencia.NAO_ALTERADA,
    maquina: str = "MAQ",
) -> ProjecaoSecao:
    return ProjecaoSecao(
        uf=uf,
        codigo_municipio=codigo,
        municipio=municipio,
        zona=zona,
        secao=secao,
        urna=urna,
        carga=carga,
        flashcard=flashcard,
        status=status,
        maquina_geracao=maquina,
    )


def _secao(*, uf: str = "AC", zona: int = 1) -> Secao:
    return Secao(
        uf=uf,
        codigo_municipio="01392",
        municipio="RIO BRANCO",
        zona=zona,
        numero=1,
        local_votacao="10",
        urna_esperada="100",
        codigo_carga="CARGA",
        flashcard="AABBCCDD",
        carga_em=None,
        status=StatusCorrespondencia.NAO_ALTERADA,
        maquina_geracao="MAQ",
        tpm_geracao="TPM",
        instalacao_geracao="INST",
        maquina_transmissao="MAQ",
        tpm_transmissao="TPM",
        instalacao_transmissao="INST",
        geracao_em=_WHEN,
    )


def _change(**overrides: object) -> MudancaGeracao:
    values: dict[str, object] = {
        "uf": "AC",
        "codigo_municipio": "01392",
        "municipio": "RIO BRANCO",
        "zona": 1,
        "secao": 10,
        "geracao_anterior": datetime(2026, 10, 3, 15, 34),
        "geracao_atual": _WHEN,
        "urna_anterior": "1",
        "urna_atual": "2",
        "carga_anterior": "A",
        "carga_atual": "A",
        "flashcard_anterior": "AA",
        "flashcard_atual": "AA",
        "local_anterior": "10",
        "local_atual": "10",
        "maquina_anterior": "M1",
        "maquina_atual": "M1",
    }
    values.update(overrides)
    return MudancaGeracao(**values)  # type: ignore[arg-type]


def _contingencia() -> Contingencia:
    return Contingencia(
        uf="AC",
        codigo_municipio="01392",
        municipio="RIO BRANCO",
        zona=1,
        urna_esperada="100",
        codigo_carga="CARGA",
        flashcard="AABBCCDD",
        carga_em=None,
        status=StatusCorrespondencia.NAO_ALTERADA,
        maquina_geracao="MAQ",
        tpm_geracao="TPM",
        instalacao_geracao="INST",
        maquina_transmissao="MAQ",
        tpm_transmissao="TPM",
        instalacao_transmissao="INST",
        geracao_em=_WHEN,
    )
