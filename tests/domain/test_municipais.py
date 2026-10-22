from datetime import date

import pytest

from eleicoes.domain.errors import DuplicateMayorError, InvalidMunicipalRowError
from eleicoes.domain.municipais import (
    CandidateRow,
    ElectorateRow,
    MunicipalRaw,
    SeatRow,
    build_municipal_results,
    parse_int,
    parse_tse_date,
)

_ORD = date(2024, 10, 6)
_SEG = date(2024, 10, 27)
_SUP = date(2025, 7, 6)


def _cand(
    ue: str,
    cargo: int,
    situacao: int,
    partido: int,
    sq: str,
    *,
    tipo: int = 2,
    data: date = _ORD,
    turno: int = 1,
    sigla: str = "PL",
) -> CandidateRow:
    return CandidateRow(
        uf="MG",
        ue=ue,
        nome_ue=f"CIDADE {ue}",
        tipo_eleicao=tipo,
        data_eleicao=data,
        turno=turno,
        cargo=cargo,
        sq_candidato=sq,
        nome_urna=f"NOME {sq}",
        partido=partido,
        sigla=sigla,
        situacao=situacao,
    )


def _aptos(ue: str, aptos: int, *, tipo: int = 2, turno: int = 1, cargo: int = 11) -> ElectorateRow:
    return ElectorateRow("MG", ue, f"CIDADE {ue}", tipo, turno, cargo, aptos)


def _raw(
    candidatos: tuple[CandidateRow, ...],
    eleitorado: tuple[ElectorateRow, ...],
    vagas: tuple[SeatRow, ...] = (),
) -> MunicipalRaw:
    return MunicipalRaw("221020260217", candidatos, eleitorado, vagas)


def test_electorate_sums_zones_of_the_ordinary_first_round_only() -> None:
    built = build_municipal_results(
        _raw(
            (),
            (
                _aptos("1", 100),
                _aptos("1", 50),
                _aptos("1", 150, turno=2),
                _aptos("1", 150, tipo=1),
                _aptos("1", 150, cargo=13),
            ),
        )
    )
    assert [item.eleitorado for item in built.municipios] == [150]


def test_second_round_winner_replaces_the_first_round_row() -> None:
    built = build_municipal_results(
        _raw(
            (
                _cand("1", 11, 6, 22, "a"),
                _cand("1", 11, 1, 22, "a", data=_SEG, turno=2),
            ),
            (_aptos("1", 10),),
        )
    )
    mayor = built.municipios[0].prefeito
    assert mayor is not None and mayor.turno == 2 and mayor.suplementar is False


def test_supplementary_election_replaces_the_ordinary_winner() -> None:
    built = build_municipal_results(
        _raw(
            (
                _cand("1", 11, 1, 55, "old", sigla="PSD"),
                _cand("1", 11, 1, 22, "new", tipo=1, data=_SUP),
            ),
            (_aptos("1", 10),),
        )
    )
    mayor = built.municipios[0].prefeito
    assert mayor is not None
    assert (mayor.partido, mayor.sq_candidato, mayor.suplementar) == (22, "new", True)
    assert built.suplementares == 1


def test_two_winners_in_the_same_election_fail() -> None:
    with pytest.raises(DuplicateMayorError):
        build_municipal_results(
            _raw((_cand("1", 11, 1, 22, "a"), _cand("1", 11, 1, 13, "b")), (_aptos("1", 10),))
        )


def test_municipality_without_winner_is_kept() -> None:
    built = build_municipal_results(_raw((_cand("48313", 11, 4, 22, "a"),), (_aptos("48313", 9),)))
    assert built.municipios[0].prefeito is None
    assert built.sem_prefeito == 1
    assert built.prefeitos == 0


def test_vice_and_null_rows_never_count() -> None:
    built = build_municipal_results(
        _raw((_cand("1", 12, 1, 22, "v"), _cand("1", 11, -1, 22, "n")), (_aptos("1", 10),))
    )
    assert built.municipios[0].prefeito is None


def test_councillors_count_qp_and_media_by_party_and_compare_with_seats() -> None:
    built = build_municipal_results(
        _raw(
            (
                _cand("1", 13, 2, 22, "a"),
                _cand("1", 13, 3, 22, "b"),
                _cand("1", 13, 2, 13, "c", sigla="PT"),
                _cand("1", 13, 5, 13, "d", sigla="PT"),
            ),
            (_aptos("1", 10),),
            (SeatRow("MG", "1", 2, 13, 3), SeatRow("MG", "2", 2, 13, 9)),
        )
    )
    assert [(item.partido, item.eleitos) for item in built.vereadores] == [(13, 1), (22, 2)]
    assert built.vereadores_eleitos == 3
    assert [(gap.ue, gap.eleitos, gap.vagas) for gap in built.divergencias] == [("2", 0, 9)]
    assert built.municipios[0].vagas_vereador == 3


def test_partial_supplementary_council_seat_adds_to_the_ordinary_ones() -> None:
    built = build_municipal_results(
        _raw(
            (_cand("1", 13, 2, 22, "a"), _cand("1", 13, 2, 22, "b", tipo=1, data=_SUP)),
            (_aptos("1", 10),),
            (SeatRow("MG", "1", 2, 13, 2), SeatRow("MG", "1", 1, 13, 1)),
        )
    )
    assert built.vereadores_eleitos == 2
    assert built.divergencias == ()


def test_mayor_outside_the_electorate_keeps_its_name_and_zero_voters() -> None:
    built = build_municipal_results(_raw((_cand("7", 11, 1, 22, "a"),), ()))
    assert [(item.ue, item.nome, item.eleitorado) for item in built.municipios] == [
        ("7", "CIDADE 7", 0)
    ]


def test_parsers_reject_bad_text() -> None:
    assert parse_tse_date("06/10/2024", "dt") == _ORD
    assert parse_int("-1", "n") == -1
    with pytest.raises(InvalidMunicipalRowError):
        parse_tse_date("2024-10-06", "dt")
    with pytest.raises(InvalidMunicipalRowError):
        parse_int("#NULO", "n")
