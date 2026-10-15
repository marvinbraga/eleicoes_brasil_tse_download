"""Brazilian half-up numbers. The percent scale matches the party-power grade."""

from fractions import Fraction
from typing import Final

_PERCENT_SCALE: Final = 10_000
_TWO_DECIMALS: Final = 100
_FOUR_DECIMALS: Final = 10_000


def round_half_up(value: Fraction) -> int:
    quotient, remainder = divmod(value.numerator, value.denominator)
    if remainder * 2 >= value.denominator:
        return quotient + 1
    return quotient


def format_integer(value: int) -> str:
    sign = "-" if value < 0 else ""
    return sign + f"{abs(value):,}".replace(",", ".")


def format_percent(share: Fraction) -> str:
    return f"{_scaled(round_half_up(share * _PERCENT_SCALE), _TWO_DECIMALS)}%"


def format_ratio(value: float) -> str:
    return format_percent(Fraction(value).limit_denominator(1_000_000_000))


def format_decimal(value: float) -> str:
    ratio = Fraction(value).limit_denominator(1_000_000_000)
    return _scaled(round_half_up(ratio * _FOUR_DECIMALS), _FOUR_DECIMALS)


def _scaled(scaled: int, scale: int) -> str:
    sign = "-" if scaled < 0 else ""
    whole, frac = divmod(abs(scaled), scale)
    width = len(str(scale)) - 1
    return f"{sign}{format_integer(whole)},{frac:0{width}d}"
