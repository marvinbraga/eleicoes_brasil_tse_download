from collections.abc import Iterator
from pathlib import Path

import pytest

from eleicoes.domain.errors import (
    ArchiveUnreadableError,
    InvalidMunicipalYearError,
    MissingIndexError,
    SchemaMismatchError,
)
from eleicoes.domain.importing import ImportCommand, ImportStatus, IndexEntry, Provenance
from eleicoes.domain.municipais import MunicipalBuild, MunicipalImportReport, MunicipalRaw
from eleicoes.domain.municipal_contract import CONSULTA_VAGAS, expected_members
from eleicoes.domain.report import EXIT_FAILURE, EXIT_NOT_PUBLISHED
from eleicoes.domain.tabular_contract import TabularContract
from eleicoes.domain.values import ElectionYear
from eleicoes.use_cases.import_municipais import ImportMunicipalTables

_ROW = '"22/10/2026";"02:16:53"' + ';"x"' * (len(CONSULTA_VAGAS.columns) - 2)
_VAGAS = ('"' + '";"'.join(CONSULTA_VAGAS.columns) + '"\r\n' + _ROW + "\r\n").encode("latin-1")


class _Member:
    def __init__(self, name: str, payload: bytes) -> None:
        self.name = name
        self.payload = payload
        self.read = False

    def read_bytes(self) -> bytes:
        self.read = True
        return self.payload


class _Opened:
    def __init__(self, members: list[_Member]) -> None:
        self.members = members

    def __iter__(self) -> Iterator[_Member]:
        return iter(self.members)

    def close(self) -> None:
        return None


class _Archives:
    def __init__(self, members: list[_Member]) -> None:
        self.members = members

    def open(self, path: Path) -> _Opened:
        del path
        return _Opened(self.members)


class _Index:
    def downloaded(self, origin: Path) -> tuple[IndexEntry, ...]:
        return (
            IndexEntry("municipais", "", "", "consulta_vagas_2024.zip", origin / "z.zip"),
            IndexEntry(
                "logs-gedai", "1", "AC", "log_gedai_1t_AC_031020261345.zip", origin / "g.zip"
            ),
        )


class _Sink:
    def __init__(self) -> None:
        self.loaded: list[tuple[str, Provenance]] = []
        self.recorded: list[tuple[str, ImportStatus]] = []

    def ensure_model(self) -> None:
        return None

    def replace_member(
        self, contract: TabularContract, provenance: Provenance, csv_bytes: bytes
    ) -> int:
        del csv_bytes
        self.loaded.append((contract.table, provenance))
        return 1

    def record(
        self, provenance: Provenance, status: ImportStatus, linhas: int, tabela: str
    ) -> None:
        del linhas, tabela
        self.recorded.append((provenance.membro, status))

    def close(self) -> None:
        return None


class _Store:
    def __init__(self) -> None:
        self.saved: list[MunicipalBuild] = []

    def read_raw(self, year: int) -> MunicipalRaw:
        del year
        return MunicipalRaw("221020260216", (), (), ())

    def save(self, year: int, built: MunicipalBuild) -> None:
        del year
        self.saved.append(built)

    def close(self) -> None:
        return None


def _run(members: list[_Member]) -> tuple[_Sink, _Store, MunicipalImportReport]:
    sink, store = _Sink(), _Store()
    use_case = ImportMunicipalTables(_Index(), _Archives(members), sink, store)
    report = use_case.execute(ImportCommand(ElectionYear(2024), Path("/o")))
    return sink, store, report


def test_uf_members_load_with_csv_generation_and_uf_and_brasil_is_never_read() -> None:
    brasil = _Member("consulta_vagas_2024_BRASIL.csv", _VAGAS)
    sink, _store, _report = _run(
        [_Member("consulta_vagas_2024_AC.csv", _VAGAS), brasil, _Member("leiame.pdf", b"")]
    )
    assert [(table, prov.uf, prov.geracao, prov.conjunto) for table, prov in sink.loaded] == [
        ("consulta_vagas", "AC", "221020260216", "municipais")
    ]
    assert ("consulta_vagas_2024_BRASIL.csv", ImportStatus.IGNORED) in sink.recorded
    assert brasil.read is False


def test_every_conjunto_and_uf_loaded_rebuilds_the_analysis() -> None:
    members = [_Member(name, _VAGAS) for name in expected_members(2024)]
    sink, store, report = _run([*members, _Member("consulta_cand_2024_BRASIL.csv", _VAGAS)])
    assert len(sink.loaded) == 78
    assert len(store.saved) == 1
    assert report.results is store.saved[0]
    assert (report.faltando, report.exit_code) == ((), 0)


def test_a_missing_uf_member_skips_the_rebuild_and_fails() -> None:
    members = [
        _Member(name, _VAGAS)
        for name in expected_members(2024)
        if name != "detalhe_votacao_munzona_2024_SP.csv"
    ]
    _sink, store, report = _run(members)
    assert store.saved == []
    assert report.results is None
    assert report.faltando == ("detalhe_votacao_munzona_2024_SP.csv",)
    assert report.exit_code == EXIT_FAILURE


def test_member_without_rows_fails_and_skips_the_rebuild() -> None:
    header_only = ('"' + '";"'.join(CONSULTA_VAGAS.columns) + '"\r\n').encode("latin-1")
    sink, store, report = _run([_Member("consulta_vagas_2024_AC.csv", header_only)])
    assert ("consulta_vagas_2024_AC.csv", ImportStatus.FAILED) in sink.recorded
    assert store.saved == []
    assert report.results is None


class _MissingIndex:
    def downloaded(self, origin: Path) -> tuple[IndexEntry, ...]:
        raise MissingIndexError(str(origin / "indice.csv"))


class _BrokenArchives:
    def open(self, path: Path) -> _Opened:
        raise ArchiveUnreadableError(str(path))


class _MismatchSink(_Sink):
    def replace_member(
        self, contract: TabularContract, provenance: Provenance, csv_bytes: bytes
    ) -> int:
        del contract, csv_bytes
        raise SchemaMismatchError(provenance.membro)


def test_missing_index_is_not_published_and_does_not_rebuild() -> None:
    store = _Store()
    use_case = ImportMunicipalTables(_MissingIndex(), _Archives([]), _Sink(), store)
    report = use_case.execute(ImportCommand(ElectionYear(2024), Path("/o")))
    assert report.exit_code == EXIT_NOT_PUBLISHED
    assert report.results is None
    assert store.saved == []


def test_unreadable_zip_fails_without_rebuilding() -> None:
    sink, store = _Sink(), _Store()
    use_case = ImportMunicipalTables(_Index(), _BrokenArchives(), sink, store)
    report = use_case.execute(ImportCommand(ElectionYear(2024), Path("/o")))
    assert sink.recorded == [("consulta_vagas_2024.zip", ImportStatus.FAILED)]
    assert report.exit_code == EXIT_FAILURE
    assert store.saved == []


def test_header_mismatch_fails_the_member_and_skips_the_rebuild() -> None:
    sink, store = _MismatchSink(), _Store()
    members = _Archives([_Member("consulta_vagas_2024_AC.csv", _VAGAS)])
    use_case = ImportMunicipalTables(_Index(), members, sink, store)
    report = use_case.execute(ImportCommand(ElectionYear(2024), Path("/o")))
    assert sink.recorded == [("consulta_vagas_2024_AC.csv", ImportStatus.FAILED)]
    assert report.results is None
    assert store.saved == []


def test_general_election_year_is_rejected_before_touching_the_sink() -> None:
    use_case = ImportMunicipalTables(_Index(), _Archives([]), _Sink(), _Store())
    with pytest.raises(InvalidMunicipalYearError):
        use_case.execute(ImportCommand(ElectionYear(2026), Path("/o")))
