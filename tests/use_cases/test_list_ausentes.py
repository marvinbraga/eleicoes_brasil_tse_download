from pathlib import Path

from eleicoes.domain.values import Turno, Uf
from eleicoes.use_cases.list_ausentes import list_ausentes

_AC_LINE = "arquivo-urna/turno-1/AC/01007/0009/0001/o03220ac0100700090001-imgbu.dat"
_MA_LINE = "arquivo-urna/turno-1/MA/08435/0050/0102/o03220ma0843500500102-imgbu.dat"
_REAL_DAT = "arquivo-urna/turno-1/BA/00001/0001/0001/real-bu.dat"


def test_lists_markers_from_every_uf_and_skips_real_files(tmp_path: Path) -> None:
    _touch(tmp_path, f"{_AC_LINE}.ausente")
    _touch(tmp_path, _REAL_DAT, b"boletim")
    _touch(tmp_path, f"{_MA_LINE}.ausente")
    (tmp_path / "arquivo-urna" / "turno-1" / "AC" / "pasta.ausente").mkdir(parents=True)
    _touch(tmp_path, "arquivo-urna/turno-2/MA/08435/0050/0102/outro-imgbu.dat.ausente")

    assert list_ausentes(tmp_path, Turno(1), None) == (_AC_LINE, _MA_LINE)
    assert list_ausentes(tmp_path, Turno(1), Uf("MA")) == (_MA_LINE,)


def test_missing_directory_returns_an_empty_tuple(tmp_path: Path) -> None:
    assert list_ausentes(tmp_path / "ausente", Turno(1), None) == ()
    assert list_ausentes(tmp_path, Turno(2), Uf("MA")) == ()


def _touch(root: Path, relative: str, payload: bytes = b"") -> None:
    path = root.joinpath(*relative.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
