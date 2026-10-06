"""Use cases over an in-memory correspondence reader."""

from datetime import datetime

import pytest

from eleicoes.domain.correspondencia import (
    Contingencia,
    MapaDeIndicios,
    MudancaGeracao,
    ProjecaoContingencia,
    ProjecaoSecao,
    ResumoUf,
    Secao,
    StatusCorrespondencia,
)
from eleicoes.domain.errors import InvalidUfError
from eleicoes.use_cases.correspondencia import (
    ListAlteredSections,
    ListarIndicios,
    ListContingencies,
    ListGenerationChanges,
    ListNewCorrespondences,
    ListSectionsOfMunicipality,
    SummarizeByUf,
    TraceSectionMedia,
)

_OLDER = datetime(2026, 10, 3, 15, 34)
_NEWER = datetime(2026, 10, 4, 12, 59)


def test_municipality_filter_is_accent_insensitive_and_unknown_is_empty() -> None:
    reader = _Reader()
    match = _secao(municipio="SÃO PAULO")
    reader.sections[None] = (match, _secao(municipio="CAMPINAS"))
    found = ListSectionsOfMunicipality(reader).execute("sp", "Sao Paulo")
    assert found == (match,)
    assert found[0].municipio == "SÃO PAULO"
    assert ListSectionsOfMunicipality(reader).execute("SP", "Nao Existe") == ()
    assert reader.calls[0] == ("secoes", "SP", None)


def test_invalid_uf_is_rejected_before_the_reader_is_used() -> None:
    reader = _Reader()
    with pytest.raises(InvalidUfError):
        ListSectionsOfMunicipality(reader).execute("XX", "RIO BRANCO")
    with pytest.raises(InvalidUfError):
        ListAlteredSections(reader).execute("br")
    assert reader.calls == []


def test_altered_sections_are_status_s_and_new_ones_are_status_star() -> None:
    reader = _Reader()
    altered = _secao(status=StatusCorrespondencia.ALTERADA)
    nova = _secao(status=StatusCorrespondencia.NOVA)
    urna = _contingencia(status=StatusCorrespondencia.NOVA)
    reader.sections[StatusCorrespondencia.ALTERADA] = (altered,)
    reader.sections[StatusCorrespondencia.NOVA] = (nova,)
    reader.contingency_rows[StatusCorrespondencia.NOVA] = (urna,)

    assert ListAlteredSections(reader).execute("AC") == (altered,)
    novas = ListNewCorrespondences(reader).execute(None)
    assert novas.secoes == (nova,)
    assert novas.contingencias == (urna,)
    assert reader.calls == [
        ("secoes", "AC", StatusCorrespondencia.ALTERADA),
        ("secoes", None, StatusCorrespondencia.NOVA),
        ("contingencias", None, StatusCorrespondencia.NOVA),
    ]


def test_contingencies_optionally_filter_the_municipality() -> None:
    reader = _Reader()
    rio = _contingencia(municipio="SÃO PAULO")
    other = _contingencia(municipio="CAMPINAS")
    reader.contingency_rows[None] = (rio, other)
    assert ListContingencies(reader).execute("ac") == (rio, other)
    assert ListContingencies(reader).execute("AC", "sao paulo") == (rio,)


def test_summary_is_ordered_by_uf() -> None:
    reader = _Reader()
    reader.summary_rows = (_resumo("SP"), _resumo("AC"))
    assert [item.uf for item in SummarizeByUf(reader).execute()] == ["AC", "SP"]


def test_generation_changes_are_the_rows_the_port_already_filtered() -> None:
    reader = _Reader()
    change = _change()
    reader.change_rows = (change,)
    assert ListGenerationChanges(reader).execute("AC") == (change,)
    assert change.campos_alterados == ("urna",)
    assert reader.calls == [("mudancas", "AC")]


def test_media_trace_is_oldest_first_and_missing_section_is_empty() -> None:
    reader = _Reader()
    newer = _secao(geracao_em=_NEWER, municipio="SÃO PAULO")
    older = _secao(geracao_em=_OLDER, municipio="SÃO PAULO")
    reader.generation_rows = (newer, _secao(municipio="CAMPINAS"), older)
    found = TraceSectionMedia(reader).execute("AC", "sao paulo", 8, 3)
    assert found == (older, newer)
    assert TraceSectionMedia(reader).execute("AC", "Belem", 8, 3) == ()
    assert reader.calls[0] == ("geracoes", "AC", 8, 3)


def test_indicios_delegates_to_the_map() -> None:
    reader = _Reader()
    projections = (
        _projecao(secao=1, carga="MESMA", urna="1"),
        _projecao(secao=2, carga="MESMA", urna="2"),
    )
    reader.projection_rows = projections
    found = ListarIndicios(reader).execute("ac")
    assert found == MapaDeIndicios().avaliar(projections, ())
    assert [item.codigo for item in found] == ["CARGA_COMPARTILHADA"]
    assert reader.calls == [
        ("projecoes", "AC"),
        ("projecoes_contingencia", "AC"),
    ]


class _Reader:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.sections: dict[StatusCorrespondencia | None, tuple[Secao, ...]] = {}
        self.contingency_rows: dict[StatusCorrespondencia | None, tuple[Contingencia, ...]] = {}
        self.summary_rows: tuple[ResumoUf, ...] = ()
        self.change_rows: tuple[MudancaGeracao, ...] = ()
        self.generation_rows: tuple[Secao, ...] = ()
        self.projection_rows: tuple[ProjecaoSecao, ...] = ()
        self.contingency_projections: tuple[ProjecaoContingencia, ...] = ()

    def secoes(self, uf: str | None, status: StatusCorrespondencia | None) -> tuple[Secao, ...]:
        self.calls.append(("secoes", uf, status))
        return self.sections.get(status, ())

    def contingencias(
        self, uf: str | None, status: StatusCorrespondencia | None
    ) -> tuple[Contingencia, ...]:
        self.calls.append(("contingencias", uf, status))
        return self.contingency_rows.get(status, ())

    def resumos(self) -> tuple[ResumoUf, ...]:
        self.calls.append(("resumos",))
        return self.summary_rows

    def mudancas(self, uf: str | None) -> tuple[MudancaGeracao, ...]:
        self.calls.append(("mudancas", uf))
        return self.change_rows

    def geracoes(self, uf: str, zona: int | None, secao: int | None) -> tuple[Secao, ...]:
        self.calls.append(("geracoes", uf, zona, secao))
        return self.generation_rows

    def projecoes(self, uf: str | None) -> tuple[ProjecaoSecao, ...]:
        self.calls.append(("projecoes", uf))
        return self.projection_rows

    def projecoes_contingencia(self, uf: str | None) -> tuple[ProjecaoContingencia, ...]:
        self.calls.append(("projecoes_contingencia", uf))
        return self.contingency_projections

    def close(self) -> None:
        self.calls.append(("close",))


def _secao(
    *,
    municipio: str = "RIO BRANCO",
    status: StatusCorrespondencia = StatusCorrespondencia.NAO_ALTERADA,
    geracao_em: datetime = _NEWER,
) -> Secao:
    return Secao(
        uf="AC",
        codigo_municipio="01392",
        municipio=municipio,
        zona=8,
        numero=3,
        local_votacao="1104",
        urna_esperada="2269941",
        codigo_carga="CARGA",
        flashcard="FA10805F",
        carga_em=None,
        status=status,
        maquina_geracao="MAQ",
        tpm_geracao="TPM",
        instalacao_geracao="INST",
        maquina_transmissao="MAQ",
        tpm_transmissao="TPM",
        instalacao_transmissao="INST",
        geracao_em=geracao_em,
    )


def _contingencia(
    *,
    municipio: str = "RIO BRANCO",
    status: StatusCorrespondencia = StatusCorrespondencia.NAO_ALTERADA,
) -> Contingencia:
    return Contingencia(
        uf="AC",
        codigo_municipio="01392",
        municipio=municipio,
        zona=8,
        urna_esperada="2269941",
        codigo_carga="CARGA",
        flashcard="FA10805F",
        carga_em=None,
        status=status,
        maquina_geracao="MAQ",
        tpm_geracao="TPM",
        instalacao_geracao="INST",
        maquina_transmissao="MAQ",
        tpm_transmissao="TPM",
        instalacao_transmissao="INST",
        geracao_em=_NEWER,
    )


def _resumo(uf: str) -> ResumoUf:
    return ResumoUf(uf, 10, 2, 3, 4, 1, 0, 5, 1)


def _change() -> MudancaGeracao:
    return MudancaGeracao(
        uf="AC",
        codigo_municipio="01392",
        municipio="RIO BRANCO",
        zona=8,
        secao=3,
        geracao_anterior=_OLDER,
        geracao_atual=_NEWER,
        urna_anterior="1",
        urna_atual="2",
        carga_anterior="A",
        carga_atual="A",
        flashcard_anterior="AA",
        flashcard_atual="AA",
        local_anterior="10",
        local_atual="10",
        maquina_anterior="M1",
        maquina_atual="M1",
    )


def _projecao(*, secao: int, carga: str, urna: str) -> ProjecaoSecao:
    return ProjecaoSecao(
        uf="AC",
        codigo_municipio="01392",
        municipio="RIO BRANCO",
        zona=8,
        secao=secao,
        urna=urna,
        carga=carga,
        flashcard="FA10805F",
        status=StatusCorrespondencia.NAO_ALTERADA,
        maquina_geracao="MAQ",
    )
