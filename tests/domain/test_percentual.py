"""Half-up display. The scale is the same one the party-power grade uses."""

from fractions import Fraction

from eleicoes.domain.percentual import format_decimal, format_integer, format_percent, format_ratio


def test_percent_is_half_up_with_a_comma() -> None:
    assert format_percent(Fraction(1, 2)) == "50,00%"
    assert format_percent(Fraction(1, 3)) == "33,33%"
    assert format_percent(Fraction(2, 3)) == "66,67%"
    assert format_percent(Fraction(12345, 100000)) == "12,35%"
    assert format_percent(Fraction(10)) == "1.000,00%"
    assert format_percent(Fraction(-1, 400)) == "-0,25%"
    assert format_ratio(0.25) == "25,00%"
    assert format_integer(1234567) == "1.234.567"
    assert format_integer(-1200) == "-1.200"
    assert format_decimal(0.5) == "0,5000"
    assert format_decimal(-1.5) == "-1,5000"
