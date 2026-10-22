from datetime import UTC, datetime

import pytest

from eleicoes.domain.errors import InvalidUfError
from eleicoes.domain.forca_municipal import (
    MunicipalTotals,
    PartyCouncil,
    PartyMayors,
    StoredMunicipalResults,
    municipal_report,
    require_municipal_uf,
)
from eleicoes.domain.partido_equivalencia import Correspondencia

_CORTE = datetime(2026, 10, 22, 2, 17)
_IMPORTADO = datetime(2026, 10, 22, 13, 5, tzinfo=UTC)
_TOTAIS = MunicipalTotals(4, 3, 1, 1, 1000, 30, 30, 0)


def _stored(
    prefeitos: tuple[PartyMayors, ...], vereadores: tuple[PartyCouncil, ...]
) -> StoredMunicipalResults:
    return StoredMunicipalResults(2024, _CORTE, _IMPORTADO, _TOTAIS, prefeitos, vereadores, ())


def test_parties_are_sorted_by_mayors_electorate_councillors_and_number() -> None:
    report = municipal_report(
        _stored(
            (
                PartyMayors(13, "PT", 1, 100),
                PartyMayors(22, "PL", 1, 300),
                PartyMayors(55, "PSD", 1, 300),
                PartyMayors(15, "MDB", 2, 50),
            ),
            (PartyCouncil(55, "PSD", 9, 3), PartyCouncil(22, "PL", 9, 2)),
        ),
        None,
    )
    assert [item.equivalente.numero_2024 for item in report.partidos] == [15, 22, 55, 13]
    assert (report.ano, report.uf, report.corte, report.totais) == (2024, None, _CORTE, _TOTAIS)


def test_party_with_councillors_only_has_zero_mayors() -> None:
    report = municipal_report(
        _stored((PartyMayors(22, "PL", 2, 300),), (PartyCouncil(50, "PSOL", 4, 2),)), "MG"
    )
    psol = report.partidos[-1]
    assert (psol.equivalente.sigla_2024, psol.prefeitos, psol.eleitorado_governado) == (
        "PSOL",
        0,
        0,
    )
    assert (psol.vereadores, psol.municipios_com_vereador) == (4, 2)
    pl = report.partidos[0]
    assert (pl.vereadores, pl.municipios_com_vereador) == (0, 0)
    assert report.uf == "MG"


def test_mayor_sigla_wins_over_the_council_sigla() -> None:
    report = municipal_report(
        _stored((PartyMayors(65, "PC do B", 1, 10),), (PartyCouncil(65, "PCdoB?", 2, 1),)), None
    )
    only = report.partidos[0]
    assert only.equivalente.correspondencia is Correspondencia.GRAFIA
    assert (only.prefeitos, only.vereadores) == (1, 2)


def test_pmb_35_becomes_democrata() -> None:
    report = municipal_report(_stored((PartyMayors(35, "PMB", 1, 10),), ()), None)
    found = report.partidos[0].equivalente
    assert found.correspondencia is Correspondencia.RENOMEADO
    assert (found.numero_2026, found.sigla_2026) == (35, "DEMOCRATA")


@pytest.mark.parametrize("uf", ["DF", "ZZ", "XX", ""])
def test_federal_district_abroad_and_unknown_ufs_are_rejected(uf: str) -> None:
    with pytest.raises(InvalidUfError):
        require_municipal_uf(uf)


def test_missing_uf_means_the_whole_country_and_case_is_normalized() -> None:
    assert require_municipal_uf(None) is None
    assert require_municipal_uf(" mg ") == "MG"
