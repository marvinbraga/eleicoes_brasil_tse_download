"""Accent-insensitive municipality names. The stored spelling is left intact."""

import unicodedata


def nomes_equivalentes(left: str, right: str) -> bool:
    return _fold(left) == _fold(right)


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return without_marks.casefold()
