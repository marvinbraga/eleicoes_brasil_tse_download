"""One terminal line per urna file. The use case calls this directly."""

from typing import TextIO

from eleicoes.domain.urna_models import UrnaAddress


class UrnaFilePresenter:
    """Rewrites the open file line. It does not keep a list of subscribers."""

    def __init__(self, output: TextIO) -> None:
        self._output = output
        self._tty = _stream_is_tty(output)
        self._width = 0
        self._live = False
        self._section: tuple[str, str, str, str] | None = None

    def begin_section(self, address: UrnaAddress) -> None:
        key = (
            address.uf.code,
            address.municipio.value,
            address.zona.value,
            address.secao.value,
        )
        if key == self._section:
            return
        self._section = key
        uf, municipio, zona, secao = key
        self._output.write(f"{uf} {municipio}  zona {zona}  seção {secao}\n")
        self._output.flush()

    def advance(self, line: str) -> None:
        if not self._tty:
            return
        self._rewrite(line)

    def outcome(self, line: str) -> None:
        if self._live:
            self._rewrite(line)
            self._output.write("\n")
            self._output.flush()
            self._live = False
            self._width = 0
            return
        self._output.write(f"{line}\n")
        self._output.flush()

    def _rewrite(self, line: str) -> None:
        pad = " " * max(0, self._width - len(line))
        self._output.write(f"\r{line}{pad}")
        self._output.flush()
        if len(line) > self._width:
            self._width = len(line)
        self._live = True


def _stream_is_tty(output: TextIO) -> bool:
    probe = getattr(output, "isatty", None)
    if not callable(probe):
        return False
    return probe() is True
