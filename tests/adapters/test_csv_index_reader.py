from pathlib import Path

import pytest

from eleicoes.adapters.csv_index_reader import CsvIndexReader
from eleicoes.domain.errors import ElectionError, MissingIndexError
from eleicoes.domain.layout import write_index
from eleicoes.domain.report import FileOutcome, TransferStatus


def test_reader_uses_the_download_index_and_skips_missing_rows(tmp_path: Path) -> None:
    filename = "CESP_1t_AC_041020261259.zip"
    write_index(
        tmp_path,
        (
            FileOutcome(filename, TransferStatus.DOWNLOADED),
            FileOutcome("ausente.zip", TransferStatus.MISSING),
        ),
    )
    entries = CsvIndexReader().downloaded(tmp_path)
    assert len(entries) == 1
    assert entries[0].conjunto == "correspondencias"
    assert entries[0].turno == "1"
    assert entries[0].uf == "AC"
    assert entries[0].arquivo == filename
    assert entries[0].path == tmp_path / "correspondencias" / "turno-1" / "AC" / filename


def test_missing_index_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(MissingIndexError):
        CsvIndexReader().downloaded(tmp_path)


def test_absolute_caminho_is_kept(tmp_path: Path) -> None:
    target = Path("/tmp/CESP_1t_AC_041020261259.zip")
    index = tmp_path / "indice.csv"
    index.write_text(
        "conjunto,turno,uf,arquivo,caminho,situacao,tamanho_bytes\n"
        f"correspondencias,1,AC,{target.name},{target.as_posix()},baixado,10\n",
        encoding="utf-8",
    )
    entries = CsvIndexReader().downloaded(tmp_path)
    assert entries[0].path == target


def test_downloaded_row_without_a_path_is_rejected(tmp_path: Path) -> None:
    index = tmp_path / "indice.csv"
    index.write_text(
        "conjunto,turno,uf,arquivo,caminho,situacao,tamanho_bytes\n"
        "correspondencias,1,AC,arquivo.zip,,baixado,10\n",
        encoding="utf-8",
    )
    with pytest.raises(ElectionError):
        CsvIndexReader().downloaded(tmp_path)
