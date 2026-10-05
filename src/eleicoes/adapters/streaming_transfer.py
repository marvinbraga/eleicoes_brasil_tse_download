from pathlib import Path
from typing import Final

from eleicoes.domain.errors import TransportError, UnexpectedHttpStatusError
from eleicoes.domain.layout import locate
from eleicoes.domain.report import TransferStatus
from eleicoes.domain.values import RemoteZip
from eleicoes.ports.http import BinaryBody, HttpClient, HttpResponse

CHUNK_SIZE: Final = 256 * 1024
HTTP_OK: Final = 200
HTTP_NOT_FOUND: Final = 404
_PROGRESS_STEP: Final = 32 * 1024 * 1024
_STATUS_LABEL: Final = {
    TransferStatus.DOWNLOADED: "baixado",
    TransferStatus.SKIPPED: "ignorado",
    TransferStatus.MISSING: "ausente",
}


class StreamingFileTransfer:
    """Grava o zip em disco por chunks. Resposta que não é HTTP 200 não é persistida."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def transfer(self, archive: RemoteZip, destination: Path) -> TransferStatus:
        target = destination / locate(archive.filename).relative_path
        if _is_complete(target):
            _announce(TransferStatus.SKIPPED, target)
            return TransferStatus.SKIPPED
        print(f"[baixando] {target}", flush=True)
        response = self._http.get(archive.url)
        try:
            status = self._persist(response, target)
        finally:
            response.body.close()
        _announce(status, target)
        return status

    def _persist(self, response: HttpResponse, target: Path) -> TransferStatus:
        if response.status_code == HTTP_NOT_FOUND:
            return TransferStatus.MISSING
        if response.status_code != HTTP_OK:
            raise UnexpectedHttpStatusError(response.status_code, target.name)
        self._write_exclusive(response.body, target)
        return TransferStatus.DOWNLOADED

    def _write_exclusive(self, body: BinaryBody, target: Path) -> None:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise TransportError("falha ao criar a pasta de destino") from exc
        partial = target.with_name(f".{target.name}.partial")
        try:
            _write_chunks(body, partial)
            partial.replace(target)
        except OSError as exc:
            _discard(partial)
            raise TransportError("falha ao gravar o arquivo") from exc
        except Exception:
            _discard(partial)
            raise


def _is_complete(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def _write_chunks(body: BinaryBody, partial: Path) -> None:
    written = 0
    announced = 0
    with partial.open("wb") as handle:
        for chunk in body.iter_chunks(CHUNK_SIZE):
            handle.write(chunk)
            written += len(chunk)
            if written - announced < _PROGRESS_STEP:
                continue
            announced = written
            print(f"[progresso] {partial.name} {written // (1024 * 1024)} MiB", flush=True)


def _announce(status: TransferStatus, target: Path) -> None:
    print(f"[{_STATUS_LABEL[status]}] {target}", flush=True)


def _discard(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return
