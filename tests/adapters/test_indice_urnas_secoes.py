"""Seções por turno e UF a partir do indice-urnas.csv."""

from pathlib import Path

import pytest

from eleicoes.adapters.indice_urnas_secoes import (
    UrnaIndexMismatchError,
    UrnaIndexMissingError,
    contar_secoes,
)
from eleicoes.domain.votos_por_estado import SecoesIndice

_HEADER = "conjunto,turno,uf,municipio,zona,secao,arquivo,caminho,situacao,tamanho_bytes"


def _row(turno: int, uf: str, secao: str, arquivo: str, situacao: str) -> str:
    caminho = f"arquivo-urna/turno-{turno}/{uf}/01066/0004/{secao}/{arquivo}"
    tamanho = "" if situacao == "ausente" else "10"
    return f"arquivo-urna,{turno},{uf},01066,0004,{secao},{arquivo},{caminho},{situacao},{tamanho}"


def _index(tmp_path: Path, *rows: str, tail: str = "") -> Path:
    path = tmp_path / "indice-urnas.csv"
    path.write_text("\n".join((_HEADER, *rows)) + "\n" + tail, encoding="utf-8")
    return path


def test_counts_listed_sections_and_those_with_a_data_bulletin(tmp_path: Path) -> None:
    path = _index(
        tmp_path,
        _row(1, "AC", "0001", "o1-bu.dat", "baixado"),
        _row(1, "AC", "0001", "o1-rdv.dat", "baixado"),
        _row(1, "AC", "0001", "o1-bu.dat", "ignorado"),
        _row(1, "AC", "0002", "o2-bu.dat", "ignorado"),
        _row(2, "AC", "0001", "o1-imgbu.dat", "ausente"),
        _row(2, "AC", "0001", "o1-bu.dat", "baixado"),
        _row(2, "AC", "0003", "o3-bu.dat", "ausente"),
        _row(2, "SE", "0009", "p-aux.json", "ausente"),
        "arquivo-urna,2,SE,,,,p-cs.json,p-cs.json,ausente,",
        "linha,quebrada",
        "arquivo-urna,x,SE,01066,0004,0001,a,b,baixado,1",
    )
    assert contar_secoes(path) == {
        (1, "AC"): SecoesIndice(2, 2),
        (2, "AC"): SecoesIndice(2, 1),
        (2, "SE"): SecoesIndice(1, 0),
    }


def test_a_line_still_being_written_is_ignored(tmp_path: Path) -> None:
    path = _index(
        tmp_path,
        _row(1, "AC", "0001", "o1-bu.dat", "baixado"),
        tail="arquivo-urna,1,AC,01066,0004,0002,o2-bu.dat,arquivo-urna/turno-1/AC",
    )
    assert contar_secoes(path) == {(1, "AC"): SecoesIndice(1, 1)}


def test_missing_index_names_the_path(tmp_path: Path) -> None:
    with pytest.raises(UrnaIndexMissingError) as error:
        contar_secoes(tmp_path / "indice-urnas.csv")
    assert error.value.caminho == tmp_path / "indice-urnas.csv"


def test_other_header_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "indice-urnas.csv"
    path.write_text("a,b,c\n", encoding="utf-8")
    with pytest.raises(UrnaIndexMismatchError):
        contar_secoes(path)
