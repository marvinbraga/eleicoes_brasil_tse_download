from collections.abc import Iterator
from pathlib import Path

from eleicoes.domain.classe_governador import (
    ClassDataset,
    ClassLine,
    ClassPlace,
    ClassReport,
    class_report,
)
from eleicoes.domain.command import DownloadCommand
from eleicoes.domain.report import RunReport, TransferStatus
from eleicoes.domain.values import (
    DiscoveryRequest,
    ElectionYear,
    RemoteZip,
    default_turnos,
    default_ufs,
)
from eleicoes.ports.ckan import CkanPackage, CkanPage


def national_request(year: int, **overrides: object) -> DiscoveryRequest:
    dataset_ref = overrides.get("dataset_ref")
    cdn_directory = overrides.get("cdn_directory")
    return DiscoveryRequest(
        year=ElectionYear(year),
        turnos=default_turnos(),
        ufs=default_ufs(),
        cdn_directory=cdn_directory if isinstance(cdn_directory, str) else None,
        dataset_ref=dataset_ref if isinstance(dataset_ref, str) else None,
    )


def command_for(year: int, destination: Path, **overrides: object) -> DownloadCommand:
    return DownloadCommand(request=national_request(year, **overrides), destination=destination)


def zip_at(url: str) -> RemoteZip:
    filename = url.rstrip("/").split("/")[-1]
    return RemoteZip(url=url, filename=filename)


class FakeCatalog:
    def __init__(self, archives: tuple[RemoteZip, ...]) -> None:
        self.archives = archives
        self.calls = 0

    def discover(self, request: DiscoveryRequest) -> tuple[RemoteZip, ...]:
        del request
        self.calls += 1
        return self.archives


class FakePublication:
    def __init__(self, published: bool) -> None:
        self.published = published
        self.calls = 0

    def is_published(self, year: ElectionYear) -> bool:
        del year
        self.calls += 1
        return self.published


class FakeTransfer:
    def __init__(self, status: TransferStatus = TransferStatus.DOWNLOADED) -> None:
        self.status = status
        self.requested: list[str] = []

    def transfer(self, archive: RemoteZip, destination: Path) -> TransferStatus:
        del destination
        self.requested.append(archive.filename)
        return self.status


class RecordingApp:
    def __init__(self, report: RunReport) -> None:
        self.report = report
        self.command: DownloadCommand | None = None

    def execute(self, command: DownloadCommand) -> RunReport:
        self.command = command
        return self.report


class FakeBody:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.closed = False
        self.reads = 0
        self.chunk_reads = 0
        self.chunk_size: int | None = None

    def iter_chunks(self, chunk_size: int) -> Iterator[bytes]:
        self.chunk_reads += 1
        self.chunk_size = chunk_size
        if not self.payload:
            return
        midpoint = max(1, len(self.payload) // 2)
        yield self.payload[:midpoint]
        rest = self.payload[midpoint:]
        if rest:
            yield rest

    def read_bytes(self) -> bytes:
        self.reads += 1
        return self.payload

    def close(self) -> None:
        self.closed = True


class FakeHttpResponse:
    def __init__(
        self,
        status_code: int,
        payload: bytes,
        content_length: int | None = None,
    ) -> None:
        self.status_code = status_code
        self.body = FakeBody(payload)
        self.content_length = content_length


class FakeHttp:
    def __init__(
        self,
        routes: dict[str, tuple[int, bytes]] | None = None,
        default: tuple[int, bytes] | None = None,
    ) -> None:
        self.routes = routes or {}
        self.default = default
        self.urls: list[str] = []
        self.responses: list[FakeHttpResponse] = []

    def get(self, url: str) -> FakeHttpResponse:
        self.urls.append(url)
        if url in self.routes:
            status, payload = self.routes[url]
        elif self.default is not None:
            status, payload = self.default
        else:
            raise AssertionError(url)
        response = FakeHttpResponse(status, payload)
        self.responses.append(response)
        return response


class MemoryGateway:
    def __init__(
        self,
        shown: dict[str, CkanPackage | None] | None = None,
        pages: tuple[CkanPage, ...] = (),
    ) -> None:
        self.shown = shown or {}
        self.pages = pages
        self.shown_ids: list[str] = []
        self.searches: list[tuple[str, int, int]] = []

    def package_show(self, package_id: str) -> CkanPackage | None:
        self.shown_ids.append(package_id)
        return self.shown.get(package_id)

    def package_search(self, query: str, *, start: int, rows: int) -> CkanPage:
        self.searches.append((query, start, rows))
        index = len(self.searches) - 1
        if index >= len(self.pages):
            return CkanPage(total=0, packages=())
        return self.pages[index]


def hand_class_dataset(df_leader: int = 22, without_uf: int = 0) -> ClassDataset:
    rows = (
        ("AC", "consolidacao", 13),
        ("AC", "consolidacao", 13),
        ("BA", "consolidacao", 13),
        ("BA", "em_aberto", 22),
        ("BA", "em_aberto", 22),
        ("DF", "em_aberto", df_leader),
    )
    places = tuple(
        ClassPlace(str(index), f"M{index}", 100, label, leader_votes(leader), uf, leader)
        for index, (uf, label, leader) in enumerate(rows)
    )
    return ClassDataset((13, 22, 44), places, (), without_uf)


def leader_votes(leader: int) -> tuple[tuple[int, int], ...]:
    return tuple((party, 10 if party == leader else 3) for party in (13, 22, 44))


def hand_class_report(without_uf: int = 0) -> ClassReport:
    dataset = hand_class_dataset(without_uf=without_uf)
    predicted = ("consolidacao", "em_aberto", "consolidacao", "em_aberto", "em_aberto", "em_aberto")
    return class_report(2026, 1, dataset, predicted, ())


def alternating_states(lines: tuple[ClassLine, ...]) -> tuple[tuple[str, str], ...]:
    codes = sorted({line.codigo for line in lines})
    return tuple((codigo, ("SP", "MG")[index % 2]) for index, codigo in enumerate(codes))
