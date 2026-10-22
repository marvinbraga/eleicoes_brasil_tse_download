"""Party registry: a federation is one proportional list."""

import pytest

from eleicoes.domain.errors import InvalidSeatRuleError, UnknownPartyRegistryError
from eleicoes.domain.federacoes import (
    REGISTRO_2026,
    Federacao,
    RegistroPartidario,
    registro_partidario,
)


def test_2026_has_five_federations_with_their_party_numbers() -> None:
    found = {federacao.codigo: federacao.partidos for federacao in REGISTRO_2026.federacoes}
    assert found == {
        "fe-brasil": (13, 65, 43),
        "psdb-cidadania": (45, 23),
        "psol-rede": (50, 18),
        "renovacao-solidaria": (25, 77),
        "uniao-progressista": (44, 11),
    }
    assert len(REGISTRO_2026.partidos) == 30


def test_legenda_is_the_federation_code_or_the_party_number() -> None:
    assert REGISTRO_2026.legenda(65) == "fe-brasil"
    assert REGISTRO_2026.legenda(11) == "uniao-progressista"
    assert REGISTRO_2026.legenda(22) == "22"
    assert REGISTRO_2026.federacao_de(22) is None


def test_registry_is_chosen_by_year() -> None:
    assert registro_partidario(2026) is REGISTRO_2026
    with pytest.raises(UnknownPartyRegistryError):
        registro_partidario(2022)


@pytest.mark.parametrize(
    "federacoes",
    [
        (Federacao("a", "A", "Federação A", (13, 99)),),
        (
            Federacao("a", "A", "Federação A", (13, 65)),
            Federacao("b", "B", "Federação B", (65, 43)),
        ),
        (
            Federacao("a", "A", "Federação A", (13, 65)),
            Federacao("a", "B", "Federação B", (43, 45)),
        ),
    ],
)
def test_registry_rejects_unknown_shared_or_repeated_members(
    federacoes: tuple[Federacao, ...],
) -> None:
    with pytest.raises(InvalidSeatRuleError):
        RegistroPartidario(2026, frozenset({13, 43, 45, 65}), federacoes)


@pytest.mark.parametrize(
    ("codigo", "partidos"),
    [("", (13, 65)), ("13", (13, 65)), ("a", (13,)), ("a", (13, 13))],
)
def test_federation_needs_a_code_and_two_distinct_parties(
    codigo: str,
    partidos: tuple[int, ...],
) -> None:
    with pytest.raises(InvalidSeatRuleError):
        Federacao(codigo, "A", "Federação A", partidos)


def test_party_numbers_stay_in_the_two_digit_range() -> None:
    with pytest.raises(InvalidSeatRuleError):
        RegistroPartidario(2026, frozenset({9}), ())
