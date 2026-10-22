"""One stderr line that says why a CLI command failed, without a traceback."""


def failure_line(headline: str, exc: BaseException) -> str:
    line = f"{headline} Motivo: {exc}"
    cause = _first_line(exc.__cause__)
    if cause:
        return f"{line} ({cause})"
    return line


def _first_line(cause: BaseException | None) -> str:
    if cause is None:
        return ""
    for line in str(cause).splitlines():
        if line.strip():
            return line.strip()
    return ""
