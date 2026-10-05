from pathlib import Path
from zipfile import ZipFile

import pytest

from eleicoes.adapters.zip_archive_reader import ZipArchiveReader
from eleicoes.domain.errors import ArchiveUnreadableError


def test_reader_returns_each_member_from_a_fixture_zip(tmp_path: Path) -> None:
    payload = '"A";"B"\r\n"1";"JORDÃO"\r\n'.encode("latin-1")
    archive_path = tmp_path / "CESP_1t_AC_041020261259.zip"
    with ZipFile(archive_path, "w") as handle:
        handle.writestr("csec_1t_AC_041020261259.csv", payload)
        handle.writestr("leiame.pdf", b"%PDF-1.5")
    opened = ZipArchiveReader().open(archive_path)
    try:
        members = {member.name: member.read_bytes() for member in opened}
    finally:
        opened.close()
    assert members["csec_1t_AC_041020261259.csv"] == payload
    assert members["leiame.pdf"].startswith(b"%PDF")


def test_missing_or_corrupt_zip_is_unreadable(tmp_path: Path) -> None:
    missing = tmp_path / "ausente.zip"
    corrupt = tmp_path / "ruim.zip"
    corrupt.write_bytes(b"not a zip")
    reader = ZipArchiveReader()
    with pytest.raises(ArchiveUnreadableError):
        reader.open(missing)
    with pytest.raises(ArchiveUnreadableError):
        reader.open(corrupt)
