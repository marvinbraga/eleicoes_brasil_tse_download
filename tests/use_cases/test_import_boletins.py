from pathlib import Path

import pytest
from tests.boletim_fakes import bulletin

from eleicoes.domain.boletim import Boletim, ImportBoletinsCommand
from eleicoes.domain.errors import InvalidBoletimContentError, InvalidBoletimError
from eleicoes.domain.report import EXIT_NOT_PUBLISHED, EXIT_SUCCESS
from eleicoes.domain.values import ElectionYear, Turno, Uf
from eleicoes.use_cases.import_boletins import ImportBoletins


def test_found_bulletins_are_loaded_for_the_command_scope(tmp_path: Path) -> None:
    relative = "01104/0005/0028/a-bu.dat"
    _write(tmp_path, relative)
    _write(tmp_path, "01104/0005/0028/a-rdv.dat", b"rdv")
    _write(tmp_path, "solto-bu.dat", b"fora")
    sink = _Sink()
    reader = _Reader({relative: bulletin(relative)})
    command = ImportBoletinsCommand(ElectionYear(2030), Turno(2), Uf("AL"), tmp_path)
    report = ImportBoletins(reader, sink).execute(command)
    assert report.exit_code == EXIT_SUCCESS
    assert report.boletins == 1
    assert report.votos == 1
    assert sink.ensured is True
    assert sink.calls == [(2030, 2, "AL", (relative,))]
    assert reader.reads == [relative]
    assert (tmp_path / relative).read_bytes() == b"bu"


def test_missing_directory_is_not_found(tmp_path: Path) -> None:
    sink = _Sink()
    report = ImportBoletins(_Reader({}), sink).execute(_command(tmp_path / "ausente"))
    assert report.exit_code == EXIT_NOT_PUBLISHED
    assert report.boletins == 0
    assert sink.calls == []
    assert sink.ensured is False


def test_directory_without_bulletins_is_not_found(tmp_path: Path) -> None:
    _write(tmp_path, "01104/0005/0028/o-rdv.dat", b"rdv")
    sink = _Sink()
    reader = _Reader({})
    report = ImportBoletins(reader, sink).execute(_command(tmp_path))
    assert report.exit_code == EXIT_NOT_PUBLISHED
    assert reader.reads == []
    assert sink.calls == []


def test_second_execute_replaces_instead_of_appending(tmp_path: Path) -> None:
    first = "01104/0005/0028/a-bu.dat"
    second = "01104/0005/0029/b-bu.dat"
    _write(tmp_path, first)
    sink = _Sink()
    reader = _Reader({first: bulletin(first), second: bulletin(second, secao=29)})
    use_case = ImportBoletins(reader, sink)
    command = _command(tmp_path)
    use_case.execute(command)
    (tmp_path / first).unlink()
    _write(tmp_path, second)
    use_case.execute(command)
    assert [item.arquivo for item in sink.current] == [second]
    assert len(sink.calls) == 2
    assert sink.calls[1][3] == (second,)


def test_reader_error_aborts_before_replace(tmp_path: Path) -> None:
    relative = "01104/0005/0028/a-bu.dat"
    _write(tmp_path, relative, b"bad")
    sink = _Sink()
    with pytest.raises(InvalidBoletimError) as caught:
        ImportBoletins(_Reader({}, error=relative), sink).execute(_command(tmp_path))
    assert caught.value.arquivo == relative
    assert sink.calls == []
    assert sink.ensured is False


def test_other_domain_error_is_named_after_the_file(tmp_path: Path) -> None:
    relative = "01104/0005/0028/a-bu.dat"
    _write(tmp_path, relative)
    with pytest.raises(InvalidBoletimError) as caught:
        ImportBoletins(_ContentReader(), _Sink()).execute(_command(tmp_path))
    assert caught.value.arquivo == relative
    assert isinstance(caught.value.__cause__, InvalidBoletimContentError)


def test_close_closes_the_sink() -> None:
    sink = _Sink()
    ImportBoletins(_Reader({}), sink).close()
    assert sink.closed is True


class _Reader:
    def __init__(self, boletins: dict[str, Boletim], error: str | None = None) -> None:
        self._boletins = boletins
        self._error = error
        self.reads: list[str] = []

    def read(self, arquivo: str, payload: bytes) -> Boletim:
        self.reads.append(arquivo)
        if payload == b"":
            raise InvalidBoletimError(arquivo)
        if arquivo == self._error:
            raise InvalidBoletimError(arquivo)
        boletim = self._boletins.get(arquivo)
        if boletim is None:
            raise InvalidBoletimError(arquivo)
        return boletim


class _ContentReader:
    def read(self, arquivo: str, _payload: bytes) -> Boletim:
        del arquivo
        raise InvalidBoletimContentError("fase")


class _Sink:
    def __init__(self) -> None:
        self.current: tuple[Boletim, ...] = ()
        self.calls: list[tuple[int, int, str, tuple[str, ...]]] = []
        self.ensured = False
        self.closed = False

    def ensure_model(self) -> None:
        self.ensured = True

    def replace_uf(
        self,
        year: ElectionYear,
        turno: Turno,
        uf: Uf,
        boletins: tuple[Boletim, ...] | list[Boletim],
    ) -> int:
        stored = tuple(boletins)
        self.current = stored
        arquivos = tuple(item.arquivo for item in stored)
        self.calls.append((year.value, turno.value, uf.code, arquivos))
        return sum(len(item.votos) for item in stored)

    def close(self) -> None:
        self.closed = True


def _command(origin: Path) -> ImportBoletinsCommand:
    return ImportBoletinsCommand(ElectionYear(2026), Turno(1), Uf("AC"), origin)


def _write(origin: Path, relative: str, payload: bytes = b"bu") -> Path:
    path = origin / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path
