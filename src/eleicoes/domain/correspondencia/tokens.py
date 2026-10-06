"""Sentinels that the correspondence files use in place of a blank value."""


def is_blank_token(value: str) -> bool:
    stripped = value.strip()
    if stripped.casefold() in {"#nulo", "#ne"}:
        return True
    return stripped in {"", "-1", "-3"}
