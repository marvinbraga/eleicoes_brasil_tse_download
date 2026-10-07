"""Downloads the urna files the divulgação index says are ready."""

import sys
import threading
from collections.abc import Callable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Final, TextIO

from eleicoes.domain.errors import (
    AnnouncedFilesMissingError,
    InvalidRequestPaceError,
    TseBlockedError,
    UnexpectedHttpStatusError,
)
from eleicoes.domain.report import TransferStatus
from eleicoes.domain.request_pace import PARALLEL_SECTIONS, RequestPace, Sleeper
from eleicoes.domain.urna_models import (
    BallotSection,
    DivulgacaoConfig,
    PleitoCode,
    UrnaAddress,
    UrnaDownloadCommand,
    UrnaLedgerRow,
    UrnaRunReport,
    urna_relative_path,
)
from eleicoes.domain.urna_urls import CONFIG_URL, UrnaUrlBuilder
from eleicoes.domain.values import Turno, Uf
from eleicoes.ports.http import HttpClient, HttpResponse
from eleicoes.ports.urna import UrnaDocuments, UrnaFileStore, UrnaLedger
from eleicoes.use_cases.urna_file_progress import UrnaFilePresenter

_HTTP_OK: Final = 200
_HTTP_FORBIDDEN: Final = 403
_HTTP_NOT_FOUND: Final = 404
_HTTP_TOO_MANY: Final = 429
_BLOCK_WAIT_SECONDS: Final = 600.0
_NOT_FOUND_LIMIT: Final = 3
_BLOCKED: Final = frozenset({_HTTP_FORBIDDEN, _HTTP_TOO_MANY})
_BAR_WIDTH: Final = 10
_KIB: Final = 1024
_MIB: Final = 1024 * 1024
_GIB: Final = 1024 * 1024 * 1024
_STORED_SUFFIXES: Final = ("bu.dat", "log.jez", "rdv.dat", "vota.vsc")
_LABEL: Final = {
    TransferStatus.DOWNLOADED: "baixado",
    TransferStatus.SKIPPED: "ignorado",
    TransferStatus.MISSING: "ausente",
}


class _Tally:
    def __init__(self) -> None:
        self.downloaded = 0
        self.skipped = 0
        self.missing = 0
        self.not_found = 0
        self.unpublished: list[int] = []
        self._lock = threading.Lock()

    def add(self, status: TransferStatus) -> bool:
        with self._lock:
            _count(self, status)
            return status is TransferStatus.MISSING and self.not_found >= _NOT_FOUND_LIMIT

    def report(self) -> UrnaRunReport:
        return UrnaRunReport(self.downloaded, self.skipped, self.missing, tuple(self.unpublished))


class DownloadUrnaFiles:
    """Calls the pace and the HTTP port directly. One request at a time per worker."""

    def __init__(
        self,
        http: HttpClient,
        pace: RequestPace,
        documents: UrnaDocuments,
        store: UrnaFileStore,
        ledger: UrnaLedger,
        sleeper: Sleeper,
        output: TextIO | None = None,
        workers: int = 1,
    ) -> None:
        if isinstance(workers, bool) or workers < 1 or workers > PARALLEL_SECTIONS:
            raise InvalidRequestPaceError(workers)
        self._http = http
        self._pace = pace
        self._documents = documents
        self._store = store
        self._ledger = ledger
        self._sleeper = sleeper
        self._workers = workers
        self._output = sys.stdout if output is None else output
        self._progress = UrnaFilePresenter(self._output)

    def execute(self, command: UrnaDownloadCommand) -> UrnaRunReport:
        config = self._load_config()
        tally = _Tally()
        for turno in command.turnos:
            self._download_turno(command, config, turno, tally)
        return tally.report()

    def _load_config(self) -> DivulgacaoConfig:
        return self._documents.read_config(self._read_required(CONFIG_URL))

    def _download_turno(
        self,
        command: UrnaDownloadCommand,
        config: DivulgacaoConfig,
        turno: Turno,
        tally: _Tally,
    ) -> None:
        pleito = config.find(command.year, turno)
        if pleito is None:
            tally.unpublished.append(turno.value)
            return
        builder = UrnaUrlBuilder(config.templates, pleito.cycle, pleito.code)
        before = tally.not_found
        ready = self._download_ufs(command, builder, turno, pleito.code, tally)
        if not ready and tally.not_found == before:
            tally.unpublished.append(turno.value)

    def _download_ufs(
        self,
        command: UrnaDownloadCommand,
        builder: UrnaUrlBuilder,
        turno: Turno,
        pleito: PleitoCode,
        tally: _Tally,
    ) -> bool:
        ready = False
        for uf in command.ufs:
            if self._download_uf(command, builder, turno, pleito, uf, tally):
                ready = True
        return ready

    def _download_uf(
        self,
        command: UrnaDownloadCommand,
        builder: UrnaUrlBuilder,
        turno: Turno,
        pleito: PleitoCode,
        uf: Uf,
        tally: _Tally,
    ) -> bool:
        url = builder.section_index(uf)
        payload = self._read_announced(
            command.destination,
            url,
            _index_row(turno, uf, url),
            tally,
            None,
        )
        if payload is None:
            return False
        ready = [item for item in self._documents.read_sections(payload, uf) if item.has_auxiliary]
        if not ready:
            return False
        self._progress.reset(len(ready))
        self._run_sections(command, builder, turno, pleito, ready, tally)
        return True

    def _run_sections(
        self,
        command: UrnaDownloadCommand,
        builder: UrnaUrlBuilder,
        turno: Turno,
        pleito: PleitoCode,
        ready: list[BallotSection],
        tally: _Tally,
    ) -> None:
        if self._workers == 1:
            for section in ready:
                self._download_section(command, builder, turno, pleito, section, tally)
            return
        _run_parallel(
            self._workers,
            [
                _section_job(self, command, builder, turno, pleito, section, tally)
                for section in ready
            ],
        )

    def _download_section(
        self,
        command: UrnaDownloadCommand,
        builder: UrnaUrlBuilder,
        turno: Turno,
        pleito: PleitoCode,
        section: BallotSection,
        tally: _Tally,
    ) -> None:
        lines: list[str] = []
        try:
            self._collect_section(command, builder, turno, pleito, section, tally, lines)
        finally:
            self._emit_section(section.address, lines)

    def _emit_section(self, address: UrnaAddress, lines: Sequence[str]) -> None:
        if not lines:
            return
        self._progress.emit_section(_section_place(address), lines, file_progress_line)

    def _collect_section(
        self,
        command: UrnaDownloadCommand,
        builder: UrnaUrlBuilder,
        turno: Turno,
        pleito: PleitoCode,
        section: BallotSection,
        tally: _Tally,
        lines: list[str],
    ) -> None:
        if self._ignore_stored_section(command, turno, pleito, section, tally, lines):
            return
        url = builder.auxiliary(section.address)
        payload = self._read_announced(
            command.destination,
            url,
            _auxiliary_row(turno, section, _leaf(url)),
            tally,
            lines,
        )
        if payload is None:
            return
        selected = self._documents.read_auxiliary(payload)
        if selected is None:
            return
        for filename in selected.filenames:
            file_url = builder.file(section.address, selected.digest, filename)
            self._transfer_file(
                command,
                turno,
                section.address,
                file_url,
                filename,
                tally,
                lines,
            )

    def _ignore_stored_section(
        self,
        command: UrnaDownloadCommand,
        turno: Turno,
        pleito: PleitoCode,
        section: BallotSection,
        tally: _Tally,
        lines: list[str],
    ) -> bool:
        names = stored_ballot_names(pleito, section.address)
        targets = [
            command.destination / urna_relative_path(turno, section.address, name) for name in names
        ]
        if not all(self._store.is_complete(target) for target in targets):
            return False
        for name, target in zip(names, targets, strict=True):
            relative = urna_relative_path(turno, section.address, name)
            self._remember(
                command.destination,
                tally,
                TransferStatus.SKIPPED,
                target,
                _file_row(
                    turno,
                    section.address,
                    name,
                    relative.as_posix(),
                    "ignorado",
                    target.stat().st_size,
                ),
                lines,
            )
        return True

    def _transfer_file(
        self,
        command: UrnaDownloadCommand,
        turno: Turno,
        address: UrnaAddress,
        file_url: str,
        filename: str,
        tally: _Tally,
        lines: list[str],
    ) -> None:
        relative = urna_relative_path(turno, address, filename)
        target = command.destination / relative
        if self._store.is_complete(target):
            self._remember(
                command.destination,
                tally,
                TransferStatus.SKIPPED,
                target,
                _file_row(
                    turno,
                    address,
                    filename,
                    relative.as_posix(),
                    "ignorado",
                    target.stat().st_size,
                ),
                lines,
            )
            return
        response = self._exchange(file_url)
        try:
            self._consume(
                response,
                command,
                turno,
                address,
                filename,
                relative,
                target,
                tally,
                lines,
            )
        finally:
            response.body.close()

    def _consume(
        self,
        response: HttpResponse,
        command: UrnaDownloadCommand,
        turno: Turno,
        address: UrnaAddress,
        filename: str,
        relative: Path,
        target: Path,
        tally: _Tally,
        lines: list[str],
    ) -> None:
        status = response.status_code
        caminho = relative.as_posix()
        if status == _HTTP_NOT_FOUND:
            self._remember(
                command.destination,
                tally,
                TransferStatus.MISSING,
                target,
                _absent_file_row(turno, address, filename, caminho),
                lines,
            )
            return
        if status != _HTTP_OK:
            raise UnexpectedHttpStatusError(status, filename)
        size = self._store.write(response.body, target)
        self._remember(
            command.destination,
            tally,
            TransferStatus.DOWNLOADED,
            target,
            _file_row(turno, address, filename, caminho, "baixado", size),
            lines,
        )

    def _read_required(self, url: str) -> bytes:
        response = self._exchange(url)
        try:
            if response.status_code != _HTTP_OK:
                raise UnexpectedHttpStatusError(response.status_code, _leaf(url))
            return response.body.read_bytes()
        finally:
            response.body.close()

    def _read_announced(
        self,
        destination: Path,
        url: str,
        row: UrnaLedgerRow,
        tally: _Tally,
        lines: list[str] | None,
    ) -> bytes | None:
        response = self._exchange(url)
        try:
            status = response.status_code
            if status == _HTTP_NOT_FOUND:
                self._remember(
                    destination,
                    tally,
                    TransferStatus.MISSING,
                    destination / row.arquivo,
                    row,
                    lines,
                )
                return None
            if status != _HTTP_OK:
                raise UnexpectedHttpStatusError(status, _leaf(url))
            return response.body.read_bytes()
        finally:
            response.body.close()

    def _exchange(self, url: str) -> HttpResponse:
        self._pace.before_request()
        response = self._http.get(url)
        if response.status_code not in _BLOCKED:
            return response
        response.body.close()
        self._sleeper.sleep(_BLOCK_WAIT_SECONDS)
        self._pace.before_request()
        retried = self._http.get(url)
        if retried.status_code not in _BLOCKED:
            return retried
        retried.body.close()
        raise TseBlockedError()

    def _remember(
        self,
        destination: Path,
        tally: _Tally,
        status: TransferStatus,
        target: Path,
        row: UrnaLedgerRow,
        lines: list[str] | None,
    ) -> None:
        line = _status_line(_LABEL[status], target.name, row.tamanho_bytes)
        abort = tally.add(status)
        if lines is None:
            self._progress.emit_lines((line,))
        else:
            lines.append(line)
        self._ledger.append(destination, row)
        if abort:
            raise AnnouncedFilesMissingError()


def _count(tally: _Tally, status: TransferStatus) -> None:
    if status is TransferStatus.DOWNLOADED:
        tally.downloaded += 1
        return
    if status is TransferStatus.SKIPPED:
        tally.skipped += 1
        return
    tally.missing += 1
    tally.not_found += 1


def _index_row(turno: Turno, uf: Uf, url: str) -> UrnaLedgerRow:
    filename = _leaf(url)
    return UrnaLedgerRow(
        turno=turno.value,
        uf=uf.code,
        municipio="",
        zona="",
        secao="",
        arquivo=filename,
        caminho=filename,
        situacao="ausente",
        tamanho_bytes=None,
    )


def _auxiliary_row(turno: Turno, section: BallotSection, filename: str) -> UrnaLedgerRow:
    relative = urna_relative_path(turno, section.address, filename)
    return _absent_file_row(turno, section.address, filename, relative.as_posix())


def _absent_file_row(
    turno: Turno,
    address: UrnaAddress,
    filename: str,
    caminho: str,
) -> UrnaLedgerRow:
    return _file_row(turno, address, filename, caminho, "ausente", None)


def stored_ballot_names(pleito: PleitoCode, address: UrnaAddress) -> tuple[str, ...]:
    """File names already used on disk for one complete section."""
    stem = (
        f"o{int(pleito.value):05d}{address.uf.code.lower()}"
        f"{address.municipio.value}{address.zona.value}{address.secao.value}"
    )
    return tuple(f"{stem}-{suffix}" for suffix in _STORED_SUFFIXES)


def progress_line(percent: int) -> str:
    """One terminal line: `[ 100% ---------- ]`."""
    filled = percent * _BAR_WIDTH // 100
    bar = f"{'-' * filled:<{_BAR_WIDTH}}"
    return f"[ {percent:>3}% {bar} ]"


def file_progress_line(received: int, total: int | None) -> str:
    """One file slot. A percent is shown only when the length is a positive int."""
    if total is not None and total > 0:
        return _percent_slot(received, total)
    return _volume_slot(received)


def format_byte_size(amount: int) -> str:
    """1024-based size. One decimal, half up; the comma appears only when it is not zero."""
    scaled = _scale_bytes(amount)
    if scaled is None:
        return f"{amount} B"
    tenths, unit = scaled
    whole, fraction = divmod(tenths, 10)
    if fraction == 0:
        return f"{whole} {unit}"
    return f"{whole},{fraction} {unit}"


def _run_parallel(workers: int, jobs: Sequence[Callable[[], None]]) -> None:
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(job) for job in jobs]
        error = _first_error(futures)
    if error is not None:
        raise error


def _section_job(
    use_case: DownloadUrnaFiles,
    command: UrnaDownloadCommand,
    builder: UrnaUrlBuilder,
    turno: Turno,
    pleito: PleitoCode,
    section: BallotSection,
    tally: _Tally,
) -> Callable[[], None]:
    def run() -> None:
        use_case._download_section(command, builder, turno, pleito, section, tally)

    return run


def _first_error(futures: Sequence[Future[None]]) -> Exception | None:
    found: Exception | None = None
    for future in as_completed(list(futures)):
        caught = _future_error(future)
        if caught is None or found is not None:
            continue
        found = caught
        _cancel_pending(futures)
    return found


def _future_error(future: Future[None]) -> Exception | None:
    try:
        future.result()
    except Exception as exc:
        return exc
    return None


def _cancel_pending(futures: Sequence[Future[None]]) -> None:
    for future in futures:
        future.cancel()


def _section_place(address: UrnaAddress) -> str:
    return (
        f"{address.uf.code} {address.municipio.value}  "
        f"zona {address.zona.value}  seção {address.secao.value}"
    )


def _percent_slot(received: int, total: int) -> str:
    tenths = min(1000, received * 1000 // total)
    label = f"{tenths // 10},{tenths % 10}%"
    filled = min(_BAR_WIDTH, received * 10 // total)
    bar = f"{'-' * filled}{'.' * (_BAR_WIDTH - filled)}"
    return f"[ {label:>6} {bar} ]"


def _volume_slot(received: int) -> str:
    return f"[ {format_byte_size(received):>8} {'.' * _BAR_WIDTH} ]"


def _scale_bytes(amount: int) -> tuple[int, str] | None:
    if amount >= _GIB:
        return _tenths(amount, _GIB), "GiB"
    if amount >= _MIB:
        return _tenths(amount, _MIB), "MiB"
    if amount >= _KIB:
        return _tenths(amount, _KIB), "KiB"
    return None


def _tenths(amount: int, divisor: int) -> int:
    return (amount * 10 + divisor // 2) // divisor


def _status_line(label: str, name: str, size: int | None) -> str:
    if label != "baixado":
        return f"[{label}] {name}"
    amount = 0 if size is None else size
    return f"[baixado] {name}  {format_byte_size(amount)}"


def _file_row(
    turno: Turno,
    address: UrnaAddress,
    filename: str,
    caminho: str,
    situacao: str,
    size: int | None,
) -> UrnaLedgerRow:
    return UrnaLedgerRow(
        turno=turno.value,
        uf=address.uf.code,
        municipio=address.municipio.value,
        zona=address.zona.value,
        secao=address.secao.value,
        arquivo=filename,
        caminho=caminho,
        situacao=situacao,
        tamanho_bytes=size,
    )


def _leaf(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]
