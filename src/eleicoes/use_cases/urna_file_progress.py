"""One contiguous terminal block per urna section."""

import threading
from collections.abc import Callable, Sequence
from typing import TextIO


class UrnaFilePresenter:
    """Writes one section block under a lock. It does not keep a subscriber list."""

    def __init__(self, output: TextIO) -> None:
        self._output = output
        self._lock = threading.Lock()
        self._done = 0
        self._total = 0

    def reset(self, total: int) -> None:
        with self._lock:
            self._done = 0
            self._total = total

    def emit_lines(self, lines: Sequence[str]) -> None:
        with self._lock:
            self._write(lines)

    def emit_section(
        self,
        place: str,
        outcomes: Sequence[str],
        header_for: Callable[[int, int], str],
    ) -> None:
        with self._lock:
            self._done += 1
            header = f"{header_for(self._done, self._total)} {place}"
            self._write((header, *outcomes))

    def _write(self, lines: Sequence[str]) -> None:
        self._output.write("".join(f"{line}\n" for line in lines))
        self._output.flush()
