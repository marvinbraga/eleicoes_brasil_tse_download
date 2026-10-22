"""Carrega os CSV municipais por UF e reconstrói as tabelas analise.municipal_*."""

from pathlib import PurePosixPath

from eleicoes.domain.errors import (
    ArchiveUnreadableError,
    InvalidGenerationError,
    MissingIndexError,
    SchemaMismatchError,
)
from eleicoes.domain.importing import (
    ImportCommand,
    ImportReport,
    ImportStatus,
    IndexEntry,
    MemberOutcome,
    Provenance,
)
from eleicoes.domain.municipais import MunicipalImportReport, build_municipal_results
from eleicoes.domain.municipal_contract import (
    MUNICIPAL_COLLECTION,
    expected_members,
    generation_from_csv,
    municipal_member,
    require_municipal_year,
)
from eleicoes.ports.archive_reader import ArchiveMember, ArchiveReader
from eleicoes.ports.index_reader import IndexReader
from eleicoes.ports.municipais import MunicipalStore
from eleicoes.ports.tabular_sink import TabularSink


class ImportMunicipalTables:
    def __init__(
        self,
        index: IndexReader,
        archives: ArchiveReader,
        sink: TabularSink,
        store: MunicipalStore,
    ) -> None:
        self._index = index
        self._archives = archives
        self._sink = sink
        self._store = store

    def execute(self, command: ImportCommand) -> MunicipalImportReport:
        year = require_municipal_year(command.year).value
        self._sink.ensure_model()
        try:
            entries = self._index.downloaded(command.origin)
        except MissingIndexError:
            return MunicipalImportReport(ImportReport(()), None)
        outcomes: list[MemberOutcome] = []
        for entry in entries:
            if entry.conjunto == MUNICIPAL_COLLECTION:
                outcomes.extend(self._zip(entry, year))
        tables = ImportReport(tuple(outcomes))
        if tables.count(ImportStatus.FAILED) > 0 or tables.count(ImportStatus.LOADED) == 0:
            return MunicipalImportReport(tables, None)
        missing = _missing(tables, year)
        if missing:
            return MunicipalImportReport(tables, None, missing)
        built = build_municipal_results(self._store.read_raw(year))
        self._store.save(year, built)
        return MunicipalImportReport(tables, built)

    def close(self) -> None:
        try:
            self._sink.close()
        finally:
            self._store.close()

    def _zip(self, entry: IndexEntry, year: int) -> tuple[MemberOutcome, ...]:
        try:
            opened = self._archives.open(entry.path)
        except ArchiveUnreadableError:
            return (self._mark(entry, entry.arquivo, "", "", ImportStatus.FAILED, ""),)
        try:
            return tuple(self._member(entry, year, member) for member in opened)
        finally:
            opened.close()

    def _member(self, entry: IndexEntry, year: int, member: ArchiveMember) -> MemberOutcome:
        found = municipal_member(member.name, year)
        if found is None:
            return self._mark(entry, member.name, "", "", ImportStatus.IGNORED, "")
        table = found.contract.table
        payload = member.read_bytes()
        try:
            stamp = generation_from_csv(member.name, payload)
        except InvalidGenerationError:
            return self._mark(entry, member.name, "", found.uf, ImportStatus.FAILED, table)
        provenance = _provenance(entry, member.name, stamp, found.uf)
        try:
            linhas = self._sink.replace_member(found.contract, provenance, payload)
        except SchemaMismatchError:
            return self._mark(entry, member.name, stamp, found.uf, ImportStatus.FAILED, table)
        return MemberOutcome(entry.arquivo, member.name, ImportStatus.LOADED, linhas, table)

    def _mark(
        self,
        entry: IndexEntry,
        membro: str,
        stamp: str,
        uf: str,
        status: ImportStatus,
        table: str,
    ) -> MemberOutcome:
        self._sink.record(_provenance(entry, membro, stamp, uf), status, 0, table)
        return MemberOutcome(entry.arquivo, membro, status, 0, table)


def _missing(tables: ImportReport, year: int) -> tuple[str, ...]:
    loaded = {
        PurePosixPath(item.membro).name
        for item in tables.outcomes
        if item.status is ImportStatus.LOADED
    }
    return tuple(name for name in expected_members(year) if name not in loaded)


def _provenance(entry: IndexEntry, membro: str, stamp: str, uf: str) -> Provenance:
    return Provenance(
        arquivo=entry.arquivo,
        membro=membro,
        geracao=stamp,
        conjunto=entry.conjunto,
        turno=entry.turno,
        uf=uf,
    )
