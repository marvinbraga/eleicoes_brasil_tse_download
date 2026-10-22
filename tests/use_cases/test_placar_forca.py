"""Strength scoreboard use case. An in-memory store stands in for Postgres."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from eleicoes.domain.errors import (
    InvalidCargoError,
    InvalidElectionYearError,
    MissingStrengthSourcesError,
)
from eleicoes.domain.forca import (
    BaseCadeiras,
    BaseMunicipal2024,
    BlocoCadeiras,
    BlocoMunicipal2024,
    Cadeiras,
    Municipal2024Forca,
)
from eleicoes.domain.stored_grade import StoredCell
from eleicoes.ports.cadeiras import (
    CadeirasUnidade,
    EstimativaCadeiras,
    Federacao,
    TotaisCadeiras,
)
from eleicoes.ports.municipal_2024 import Municipal2024, MunicipalPartido2024, TotaisMunicipal2024
from eleicoes.ports.relatorio_poder import StoredReport
from eleicoes.use_cases.placar_forca import MontarPlacarForca

_MOMENT = datetime(2026, 10, 22, tzinfo=UTC)
_UF = StoredCell("uf", "AC", "Acre", 100, 22, 30, 0)
_PAIS = StoredCell("pais", "BR", "Brasil", 100, 22, 30, 0)
_CITY = StoredCell("municipio", "1", "RIO BRANCO (AC)", 100, 22, 30, 0)


class _Store:
    def __init__(self, stored: dict[str, StoredReport | None]) -> None:
        self.stored = stored
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    async def load(self, _ano: int, _turno: int, _cargo: str) -> StoredReport | None:
        raise AssertionError("the scoreboard reads levels only")

    async def save(
        self,
        _ano: int,
        _turno: int,
        _cargo: str,
        _cells: tuple[StoredCell, ...],
    ) -> datetime:
        raise AssertionError("the scoreboard never writes")

    async def load_levels(
        self,
        _ano: int,
        _turno: int,
        cargo: str,
        niveis: tuple[str, ...],
    ) -> StoredReport | None:
        self.calls.append((cargo, niveis))
        found = self.stored.get(cargo)
        if found is None:
            return None
        kept = tuple(cell for cell in found.cells if cell.nivel in niveis)
        return StoredReport(kept, found.gerado_em)


_CARGOS = ("presidente", "governador", "senador", "deputadoFederal", "deputadoEstadual")


def _all() -> dict[str, StoredReport | None]:
    cells = (_UF, _PAIS, _CITY)
    return {cargo: StoredReport(cells, _MOMENT) for cargo in _CARGOS}


def test_default_reference_reads_one_municipal_level() -> None:
    store = _Store(_all())
    placar = asyncio.run(MontarPlacarForca(store).execute(2026, 1, "deputadoEstadual"))
    assert store.calls == [
        ("presidente", ("pais", "uf")),
        ("deputadoFederal", ("pais", "uf")),
        ("deputadoEstadual", ("uf", "municipio")),
    ]
    assert placar.faltando == ()
    assert placar.pais.base.municipal is not None


def test_governor_reference_adds_a_fourth_read() -> None:
    store = _Store(_all())
    asyncio.run(MontarPlacarForca(store).execute(2026, 1, "governador"))
    assert store.calls[-1] == ("governador", ("municipio",))
    assert len(store.calls) == 4


def test_president_reference_reads_its_cities_in_the_same_call() -> None:
    store = _Store(_all())
    asyncio.run(MontarPlacarForca(store).execute(2026, 1, "presidente"))
    assert store.calls[0] == ("presidente", ("pais", "uf", "municipio"))
    assert len(store.calls) == 3


def test_empty_or_absent_reports_degrade_per_office() -> None:
    stored = _all()
    stored["presidente"] = None
    stored["deputadoFederal"] = StoredReport((), _MOMENT)
    placar = asyncio.run(MontarPlacarForca(_Store(stored)).execute(2026, 1, "deputadoEstadual"))
    assert placar.faltando == ("presidente", "deputadoFederal")


def test_nothing_stored_is_a_conflict_with_every_command() -> None:
    with pytest.raises(MissingStrengthSourcesError) as caught:
        asyncio.run(MontarPlacarForca(_Store({})).execute(2026, 1, "deputadoEstadual"))
    assert caught.value.cargos == ("presidente", "deputadoFederal", "deputadoEstadual")
    assert "--cargo deputadoFederal --sem-navegador" in str(caught.value)


def test_bad_input_fails_before_any_read() -> None:
    store = _Store(_all())
    with pytest.raises(InvalidCargoError):
        asyncio.run(MontarPlacarForca(store).execute(2026, 1, "deputadoDistrital"))
    with pytest.raises(InvalidElectionYearError):
        asyncio.run(MontarPlacarForca(store).execute(1900, 1, "deputadoEstadual"))
    assert store.calls == []


def _city(partido: int, votos: int) -> StoredCell:
    return StoredCell("municipio", "1", "RIO BRANCO (AC)", 100, partido, votos, 0)


def _seats_stored() -> dict[str, StoredReport | None]:
    stored = _all()
    cells = (_UF, _PAIS, _city(22, 30), _city(13, 20), _city(43, 20))
    stored["deputadoEstadual"] = StoredReport(cells, _MOMENT)
    return stored


def _row(chave: str, uf: str, camara: int) -> CadeirasUnidade:
    # Distinct values per field, so a swapped field cannot pass.
    return CadeirasUnidade(chave, uf, camara, camara + 1, camara + 2, camara + 3, camara * 2)


_ESTIMATE = EstimativaCadeiras(
    ano=2026,
    turno=1,
    gerado_em=_MOMENT,
    federacoes=(Federacao("fe-brasil", "Federação Brasil da Esperança", (13, 65, 43)),),
    totais=TotaisCadeiras(camara=513, senado=54, governadores=27, assembleias=1059),
    linhas=(
        _row("22", "AC", 3),
        _row("13", "AC", 2),
        _row("43", "AC", 1),
        _row("fed:fe-brasil", "AC", 3),
        _row("22", "BR", 119),
        _row("fed:fe-brasil", "BR", 87),
    ),
)


class _Seats:
    def __init__(self, estimate: EstimativaCadeiras | None) -> None:
        self.estimate = estimate
        self.calls: list[tuple[int, int]] = []

    async def load(self, ano: int, turno: int) -> EstimativaCadeiras | None:
        self.calls.append((ano, turno))
        return self.estimate


def test_seat_estimate_brings_federations_and_seats() -> None:
    seats = _Seats(_ESTIMATE)
    use_case = MontarPlacarForca(_Store(_seats_stored()), cadeiras=seats)
    placar = asyncio.run(use_case.execute(2026, 1, "deputadoEstadual"))
    assert seats.calls == [(2026, 1)]
    assert placar.cadeiras == BlocoCadeiras(True, BaseCadeiras(513, 54, 27, 1059))
    partidos = {unidade.chave: unidade for unidade in placar.pais.unidades}
    federadas = {unidade.chave: unidade for unidade in placar.pais.federadas}
    assert list(federadas) == ["fed:fe-brasil", "22"]
    federacao = federadas["fed:fe-brasil"]
    assert (federacao.tipo, federacao.nome) == ("federacao", "Federação Brasil da Esperança")
    assert federacao.cadeiras == Cadeiras(87, 88, 89, 90, 174)
    assert partidos["22"].cadeiras == Cadeiras(119, 120, 121, 122, 238)
    # 13 and 43 alone lose the city to 22 (30); joined they lead it (40).
    assert federacao.municipal is not None and federacao.municipal.lidera == 1
    assert partidos["22"].municipal is not None and partidos["22"].municipal.lidera == 1
    assert federadas["22"].municipal is not None and federadas["22"].municipal.lidera == 0
    acre = placar.ufs[0]
    assert acre.base.cadeiras == BaseCadeiras(6, 9, 1, 12)
    assert [unidade.chave for unidade in acre.federadas] == ["fed:fe-brasil", "22"]
    assert acre.federadas[0].cadeiras == Cadeiras(3, 4, 5, 6, 6)


@pytest.mark.parametrize(("ano", "turno"), [(2026, 2), (2022, 1)])
def test_seat_port_is_not_asked_when_the_simulation_does_not_apply(ano: int, turno: int) -> None:
    seats = _Seats(_ESTIMATE)
    use_case = MontarPlacarForca(_Store(_seats_stored()), cadeiras=seats)
    placar = asyncio.run(use_case.execute(ano, turno, "deputadoEstadual"))
    assert seats.calls == []
    assert placar.cadeiras is None
    assert placar.pais.federadas == ()


def test_missing_estimate_keeps_parties_only_and_flags_the_block() -> None:
    use_case = MontarPlacarForca(_Store(_seats_stored()), cadeiras=_Seats(None))
    placar = asyncio.run(use_case.execute(2026, 1, "deputadoEstadual"))
    assert placar.cadeiras == BlocoCadeiras(False, None)
    assert all(unidade.tipo == "partido" for unidade in placar.pais.unidades)
    assert placar.pais.federadas == ()
    assert all(unidade.cadeiras is None for unidade in placar.pais.unidades)


def test_without_the_seat_port_the_block_is_absent() -> None:
    placar = asyncio.run(MontarPlacarForca(_Store(_seats_stored())).execute(2026, 1, "governador"))
    assert placar.cadeiras is None
    assert all(unidade.tipo == "partido" for unidade in placar.pais.unidades)


_CORTE = datetime(2026, 10, 1, tzinfo=UTC)
_MUNICIPAL = Municipal2024(
    data_corte=_CORTE,
    importado_em=_MOMENT,
    equivalencia_versao="2026-10-22",
    totais=(
        TotaisMunicipal2024("AC", 22, 22, 600, 230),
        TotaisMunicipal2024("BR", 5569, 5560, 155912680, 58000),
    ),
    linhas=(
        MunicipalPartido2024(13, "AC", 3, 50, 20),
        MunicipalPartido2024(43, "AC", 1, 10, 5),
        MunicipalPartido2024(13, "BR", 250, 900, 3000),
        MunicipalPartido2024(22, "BR", 500, 2000, 4000),
    ),
    sem_correspondencia=(31,),
)


class _Municipal:
    def __init__(self, found: Municipal2024 | None) -> None:
        self.found = found
        self.calls = 0

    async def load(self) -> Municipal2024 | None:
        self.calls += 1
        return self.found


def test_2024_counts_reach_parties_and_federations() -> None:
    municipal = _Municipal(_MUNICIPAL)
    use_case = MontarPlacarForca(
        _Store(_seats_stored()), cadeiras=_Seats(_ESTIMATE), municipal_2024=municipal
    )
    placar = asyncio.run(use_case.execute(2026, 1, "deputadoEstadual"))
    assert municipal.calls == 1
    totais_br = BaseMunicipal2024(5569, 5560, 155912680, 58000)
    assert placar.municipal_2024 == BlocoMunicipal2024(True, _CORTE, totais_br)
    partidos = {unidade.chave: unidade for unidade in placar.pais.unidades}
    assert partidos["22"].municipal_2024 == Municipal2024Forca(500, 2000, 4000)
    assert partidos["43"].municipal_2024 == Municipal2024Forca(0, 0, 0)
    acre = placar.ufs[0]
    assert acre.base.municipal_2024 == BaseMunicipal2024(22, 22, 600, 230)
    federacao = acre.federadas[0]
    assert (federacao.chave, federacao.municipal_2024) == (
        "fed:fe-brasil",
        Municipal2024Forca(4, 60, 25),
    )


def test_missing_2024_import_flags_the_block_and_absent_port_leaves_it_out() -> None:
    flagged = MontarPlacarForca(_Store(_seats_stored()), municipal_2024=_Municipal(None))
    placar = asyncio.run(flagged.execute(2026, 1, "deputadoEstadual"))
    assert placar.municipal_2024 == BlocoMunicipal2024(False, None, None)
    assert all(unidade.municipal_2024 is None for unidade in placar.pais.unidades)
    plain = asyncio.run(MontarPlacarForca(_Store(_seats_stored())).execute(2026, 1, "governador"))
    assert plain.municipal_2024 is None


def test_2024_block_is_left_out_for_a_year_without_2026_party_numbers() -> None:
    municipal = _Municipal(_MUNICIPAL)
    use_case = MontarPlacarForca(_Store(_seats_stored()), municipal_2024=municipal)
    placar = asyncio.run(use_case.execute(2022, 1, "deputadoEstadual"))
    assert municipal.calls == 0
    assert placar.municipal_2024 is None


def test_rows_added_for_2024_counts_also_get_their_seats() -> None:
    found = replace(
        _MUNICIPAL, linhas=(*_MUNICIPAL.linhas, MunicipalPartido2024(10, "AC", 5, 40, 62))
    )
    estimate = replace(_ESTIMATE, linhas=(*_ESTIMATE.linhas, _row("10", "AC", 1)))
    use_case = MontarPlacarForca(
        _Store(_seats_stored()), cadeiras=_Seats(estimate), municipal_2024=_Municipal(found)
    )
    placar = asyncio.run(use_case.execute(2026, 1, "deputadoEstadual"))
    novo = next(unidade for unidade in placar.ufs[0].unidades if unidade.chave == "10")
    assert novo.municipal_2024 == Municipal2024Forca(5, 40, 62)
    assert novo.cadeiras == Cadeiras(1, 2, 3, 4, 2)


def test_2024_count_of_a_member_without_2026_votes_joins_the_federation() -> None:
    found = replace(
        _MUNICIPAL, linhas=(*_MUNICIPAL.linhas, MunicipalPartido2024(65, "AC", 7, 70, 7))
    )
    use_case = MontarPlacarForca(
        _Store(_seats_stored()), cadeiras=_Seats(_ESTIMATE), municipal_2024=_Municipal(found)
    )
    placar = asyncio.run(use_case.execute(2026, 1, "deputadoEstadual"))
    federadas = {unidade.chave: unidade for unidade in placar.ufs[0].federadas}
    assert "65" not in federadas
    assert federadas["fed:fe-brasil"].partidos == (13, 43, 65)
    assert federadas["fed:fe-brasil"].municipal_2024 == Municipal2024Forca(11, 130, 32)


def test_second_round_keeps_2024_without_seats_or_federations() -> None:
    seats = _Seats(_ESTIMATE)
    use_case = MontarPlacarForca(
        _Store(_seats_stored()), cadeiras=seats, municipal_2024=_Municipal(_MUNICIPAL)
    )
    placar = asyncio.run(use_case.execute(2026, 2, "deputadoEstadual"))
    assert seats.calls == []
    assert placar.municipal_2024 is not None and placar.municipal_2024.disponivel
    assert placar.cadeiras is None
    assert placar.pais.federadas == ()
    assert all(uf.federadas == () for uf in placar.ufs)
