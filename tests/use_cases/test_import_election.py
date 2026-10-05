from pathlib import Path

from eleicoes.domain.errors import (
    ArchiveUnreadableError,
    MissingIndexError,
    SchemaMismatchError,
)
from eleicoes.domain.importing import ImportCommand, ImportStatus, IndexEntry, Provenance
from eleicoes.domain.tabular_contract import TabularContract
from eleicoes.domain.values import ElectionYear
from eleicoes.use_cases.import_election import ImportElectionTables


def test_csv_is_loaded_and_pdf_is_ignored_without_reading_it() -> None:
    pdf = _Member("leiame.pdf", b"%PDF")
    csv_member = _Member("csec_1t_AC_041020261259.csv", b"csv")
    archives = _Archives({_PATH: (csv_member, pdf)})
    sink = _Sink()
    use_case = _use_case(_entries(), archives, sink)
    report = use_case.execute(_command())
    use_case.close()
    assert report.exit_code == 0
    assert report.count(ImportStatus.LOADED) == 1
    assert sink.replaced == [("csec", csv_member.name, b"csv")]
    assert sink.records[0][1] is ImportStatus.IGNORED
    assert pdf.reads == 0
    assert archives.opened[0].closed is True
    assert sink.ensured is True
    assert sink.closed is True


def test_schema_mismatch_fails_that_member_and_continues() -> None:
    csv_member = _Member("csec_1t_AC_041020261259.csv", b"bad")
    pdf = _Member("leiame.pdf", b"%PDF")
    sink = _Sink(bad={csv_member.name})
    report = _use_case(_entries(), _Archives({_PATH: (csv_member, pdf)}), sink).execute(_command())
    assert report.exit_code == 1
    assert report.count(ImportStatus.FAILED) == 1
    assert report.count(ImportStatus.IGNORED) == 1
    assert sink.replaced == []


def test_missing_index_exits_quietly() -> None:
    sink = _Sink()
    report = _use_case((), _Archives({}), sink, missing=True).execute(_command())
    assert report.exit_code == 2
    assert sink.ensured is True
    assert sink.records == []


def test_only_ignored_members_mean_nothing_tabular() -> None:
    pdf = _Member("leiame.pdf", b"%PDF")
    report = _use_case(_entries(), _Archives({_PATH: (pdf,)}), _Sink()).execute(_command())
    assert report.exit_code == 2


def test_unreadable_zip_is_a_failed_member() -> None:
    sink = _Sink()
    report = _use_case(_entries(), _Archives({}), sink).execute(_command())
    assert report.exit_code == 1
    assert sink.records[0][1] is ImportStatus.FAILED


def test_filename_without_a_stamp_fails_before_opening() -> None:
    entry = IndexEntry("correspondencias", "1", "AC", "sem-carimbo.zip", _PATH)
    archives = _Archives({_PATH: ()})
    report = _use_case((entry,), archives, _Sink()).execute(_command())
    assert report.exit_code == 1
    assert archives.opened == []


class _Member:
    def __init__(self, name: str, payload: bytes) -> None:
        self.name = name
        self.payload = payload
        self.reads = 0

    def read_bytes(self) -> bytes:
        self.reads += 1
        return self.payload


class _Opened:
    def __init__(self, members: tuple[_Member, ...]) -> None:
        self._members = members
        self.closed = False

    def __iter__(self) -> object:
        return iter(self._members)

    def close(self) -> None:
        self.closed = True


class _Archives:
    def __init__(self, mapping: dict[Path, tuple[_Member, ...]]) -> None:
        self.mapping = mapping
        self.opened: list[_Opened] = []

    def open(self, path: Path) -> _Opened:
        if path not in self.mapping:
            raise ArchiveUnreadableError(str(path))
        opened = _Opened(self.mapping[path])
        self.opened.append(opened)
        return opened


class _Index:
    def __init__(self, entries: tuple[IndexEntry, ...], missing: bool) -> None:
        self.entries = entries
        self.missing = missing

    def downloaded(self, origin: Path) -> tuple[IndexEntry, ...]:
        del origin
        if self.missing:
            raise MissingIndexError("indice.csv")
        return self.entries


class _Sink:
    def __init__(self, bad: set[str] | None = None) -> None:
        self.bad = bad or set()
        self.ensured = False
        self.replaced: list[tuple[str, str, bytes]] = []
        self.records: list[tuple[str, ImportStatus, int, str]] = []
        self.closed = False

    def ensure_model(self) -> None:
        self.ensured = True

    def replace_member(
        self,
        contract: TabularContract,
        provenance: Provenance,
        csv_bytes: bytes,
    ) -> int:
        if provenance.membro in self.bad:
            raise SchemaMismatchError(provenance.membro)
        self.replaced.append((contract.table, provenance.membro, csv_bytes))
        return 4

    def record(
        self,
        provenance: Provenance,
        status: ImportStatus,
        linhas: int,
        tabela: str,
    ) -> None:
        self.records.append((provenance.membro, status, linhas, tabela))

    def close(self) -> None:
        self.closed = True


def _use_case(
    entries: tuple[IndexEntry, ...],
    archives: _Archives,
    sink: _Sink,
    *,
    missing: bool = False,
) -> ImportElectionTables:
    return ImportElectionTables(index=_Index(entries, missing), archives=archives, sink=sink)


def _entries() -> tuple[IndexEntry, ...]:
    return (IndexEntry("correspondencias", "1", "AC", "CESP_1t_AC_041020261259.zip", _PATH),)


def _command() -> ImportCommand:
    return ImportCommand(ElectionYear(2026), Path("downloads/2026"))


_PATH = Path("downloads/2026/correspondencias/turno-1/AC/CESP_1t_AC_041020261259.zip")
