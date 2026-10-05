"""Carrega CSV de correspondência e registra o que não é tabular."""

from eleicoes.domain.errors import (
    ArchiveUnreadableError,
    InvalidGenerationError,
    MissingIndexError,
    SchemaMismatchError,
)
from eleicoes.domain.importing import (
    Generation,
    ImportCommand,
    ImportReport,
    ImportStatus,
    IndexEntry,
    MemberOutcome,
    Provenance,
)
from eleicoes.domain.tabular_contract import TabularContract, contract_for
from eleicoes.ports.archive_reader import ArchiveMember, ArchiveReader
from eleicoes.ports.index_reader import IndexReader
from eleicoes.ports.tabular_sink import TabularSink


class ImportElectionTables:
    """Percorre o índice e grava cada membro pela porta TabularSink."""

    def __init__(self, index: IndexReader, archives: ArchiveReader, sink: TabularSink) -> None:
        self._index = index
        self._archives = archives
        self._sink = sink

    def execute(self, command: ImportCommand) -> ImportReport:
        self._sink.ensure_model()
        try:
            entries = self._index.downloaded(command.origin)
        except MissingIndexError:
            return ImportReport(())
        outcomes: list[MemberOutcome] = []
        for entry in entries:
            outcomes.extend(self._zip(entry))
        return ImportReport(tuple(outcomes))

    def close(self) -> None:
        self._sink.close()

    def _zip(self, entry: IndexEntry) -> tuple[MemberOutcome, ...]:
        try:
            stamp = Generation.from_filename(entry.arquivo).stamp
        except InvalidGenerationError:
            return (self._fail(entry, entry.arquivo, ""),)
        try:
            opened = self._archives.open(entry.path)
        except ArchiveUnreadableError:
            return (self._fail(entry, entry.arquivo, stamp),)
        outcomes: list[MemberOutcome] = []
        try:
            for member in opened:
                outcomes.append(self._member(entry, stamp, member))
        finally:
            opened.close()
        return tuple(outcomes)

    def _member(self, entry: IndexEntry, stamp: str, member: ArchiveMember) -> MemberOutcome:
        contract = contract_for(member.name)
        provenance = _provenance(entry, member.name, stamp)
        if contract is None:
            self._sink.record(provenance, ImportStatus.IGNORED, 0, "")
            return _outcome(entry.arquivo, member.name, ImportStatus.IGNORED, 0, "")
        return self._load(entry, provenance, contract, member)

    def _load(
        self,
        entry: IndexEntry,
        provenance: Provenance,
        contract: TabularContract,
        member: ArchiveMember,
    ) -> MemberOutcome:
        try:
            linhas = self._sink.replace_member(contract, provenance, member.read_bytes())
        except SchemaMismatchError:
            self._sink.record(provenance, ImportStatus.FAILED, 0, contract.table)
            return _outcome(entry.arquivo, member.name, ImportStatus.FAILED, 0, contract.table)
        return _outcome(entry.arquivo, member.name, ImportStatus.LOADED, linhas, contract.table)

    def _fail(self, entry: IndexEntry, membro: str, stamp: str) -> MemberOutcome:
        self._sink.record(_provenance(entry, membro, stamp), ImportStatus.FAILED, 0, "")
        return _outcome(entry.arquivo, membro, ImportStatus.FAILED, 0, "")


def _provenance(entry: IndexEntry, membro: str, stamp: str) -> Provenance:
    return Provenance(
        arquivo=entry.arquivo,
        membro=membro,
        geracao=stamp,
        conjunto=entry.conjunto,
        turno=entry.turno,
        uf=entry.uf,
    )


def _outcome(
    arquivo: str,
    membro: str,
    status: ImportStatus,
    linhas: int,
    tabela: str,
) -> MemberOutcome:
    return MemberOutcome(arquivo, membro, status, linhas, tabela)
