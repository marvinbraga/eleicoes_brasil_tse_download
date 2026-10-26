"""The TSE munzona zips: only the president member, summed over zones and transit votes."""

from pathlib import Path
from zipfile import ZipFile

import pytest

from eleicoes.adapters.munzona_presidente import (
    MunzonaMemberMissingError,
    ler_presidente_munzona,
    url_munzona,
)
from eleicoes.domain.errors import ArchiveUnreadableError

_VOTOS = (
    "NR_TURNO",
    "SG_UF",
    "CD_MUNICIPIO",
    "NM_MUNICIPIO",
    "NR_ZONA",
    "CD_CARGO",
    "NR_CANDIDATO",
    "ST_VOTO_EM_TRANSITO",
    "QT_VOTOS_NOMINAIS_VALIDOS",
)
_DETALHE = (
    "NR_TURNO",
    "SG_UF",
    "CD_MUNICIPIO",
    "NM_MUNICIPIO",
    "NR_ZONA",
    "CD_CARGO",
    "QT_VOTOS_BRANCOS",
    "QT_TOTAL_VOTOS_NULOS",
)


def test_reads_both_rounds_summing_zones_and_transit(tmp_path: Path) -> None:
    votos = _zip(
        tmp_path / "votos.zip",
        "votacao_candidato_munzona_2022_BR.csv",
        _VOTOS,
        (
            ("1", "AC", "1120", "ACRELÂNDIA", "8", "1", "13", "N", "300"),
            ("1", "AC", "1120", "ACRELÂNDIA", "9", "1", "13", "S", "20"),
            ("1", "AC", "1120", "ACRELÂNDIA", "8", "1", "22", "N", "500"),
            ("1", "AC", "1120", "ACRELÂNDIA", "8", "1", "15", "N", "0"),
            ("1", "AC", "1120", "ACRELÂNDIA", "8", "3", "13", "N", "999"),
            ("2", "AC", "1120", "ACRELÂNDIA", "8", "1", "13", "N", "330"),
            ("2", "AC", "1120", "ACRELÂNDIA", "8", "1", "22", "N", "510"),
            ("2", "ZZ", "29262", "ABU DHABI", "1", "1", "22", "N", "7"),
        ),
        extra="votacao_candidato_munzona_2022_BRASIL.csv",
    )
    detalhe = _zip(
        tmp_path / "detalhe.zip",
        "detalhe_votacao_munzona_2022_BR.csv",
        _DETALHE,
        (
            ("1", "AC", "1120", "ACRELÂNDIA", "8", "1", "10", "12"),
            ("1", "AC", "1120", "ACRELÂNDIA", "9", "1", "1", "2"),
            ("2", "AC", "1120", "ACRELÂNDIA", "8", "1", "5", "6"),
            ("1", "RR", "3000", "SEM VOTOS", "1", "1", "1", "1"),
        ),
    )

    found = ler_presidente_munzona(votos, detalhe)

    assert sorted(found) == [1, 2]
    (primeiro,) = found[1]
    assert (primeiro.uf, primeiro.codigo, primeiro.nome) == ("AC", "1120", "ACRELÂNDIA")
    assert [(party.partido, party.votos) for party in primeiro.presidente.parties] == [
        (13, 320),
        (22, 500),
    ]
    assert (primeiro.presidente.branco, primeiro.presidente.nulo) == (11, 14)
    assert [(place.uf, place.presidente.valid) for place in found[2]] == [("AC", 840), ("ZZ", 7)]


def test_archive_without_the_president_member_is_rejected(tmp_path: Path) -> None:
    votos = _zip(tmp_path / "votos.zip", "votacao_candidato_munzona_2022_BRASIL.csv", _VOTOS, ())

    with pytest.raises(MunzonaMemberMissingError):
        ler_presidente_munzona(votos, votos)


def test_unreadable_archive_is_rejected(tmp_path: Path) -> None:
    quebrado = tmp_path / "quebrado.zip"
    quebrado.write_bytes(b"isto nao e um zip")

    with pytest.raises(ArchiveUnreadableError):
        ler_presidente_munzona(quebrado, quebrado)


def test_open_data_url() -> None:
    assert url_munzona("detalhe_votacao_munzona", 2022) == (
        "https://cdn.tse.jus.br/estatistica/sead/odsele/detalhe_votacao_munzona/"
        "detalhe_votacao_munzona_2022.zip"
    )


def _zip(
    path: Path,
    membro: str,
    header: tuple[str, ...],
    rows: tuple[tuple[str, ...], ...],
    *,
    extra: str | None = None,
) -> Path:
    linhas = [";".join(f'"{campo}"' for campo in header)]
    linhas.extend(";".join(f'"{campo}"' for campo in row) for row in rows)
    with ZipFile(path, "w") as archive:
        if extra is not None:
            archive.writestr(extra, b"lixo que nao deve ser lido")
        archive.writestr(membro, ("\r\n".join(linhas) + "\r\n").encode("latin-1"))
    return path
