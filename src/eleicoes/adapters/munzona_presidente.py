"""Votos de presidente por município nos zips munzona dos dados abertos do TSE.

Lê só o membro `*_BR.csv` de cada zip, que traz o cargo de presidente dos dois
turnos em todas as UFs e no exterior (ZZ). O membro `*_BRASIL.csv` repete todos
os cargos e é ignorado. Zonas e voto em trânsito somam no município.
"""

import csv
import io
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final
from zipfile import BadZipFile, ZipFile

from eleicoes.domain.errors import ArchiveUnreadableError, ElectionError
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally

DADOS_ABERTOS: Final = "https://cdn.tse.jus.br/estatistica/sead/odsele"
VOTOS_POR_CANDIDATO: Final = "votacao_candidato_munzona"
DETALHE_DA_VOTACAO: Final = "detalhe_votacao_munzona"
CARGO_PRESIDENTE: Final = "1"
_SUFIXO_DO_MEMBRO: Final = "_BR.csv"
_CODIFICACAO: Final = "latin-1"
_SEPARADOR: Final = ";"

Chave = tuple[int, str, str]


class MunzonaMemberMissingError(ElectionError):
    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"no presidential member (*{_SUFIXO_DO_MEMBRO}) in {path}")


@dataclass(slots=True)
class _Municipio:
    nome: str
    votos: dict[int, int] = field(default_factory=dict)
    branco: int = 0
    nulo: int = 0


def url_munzona(conjunto: str, ano: int) -> str:
    return f"{DADOS_ABERTOS}/{conjunto}/{conjunto}_{ano}.zip"


def ler_presidente_munzona(votos: Path, detalhe: Path) -> dict[int, tuple[MunicipalPlace, ...]]:
    """Os municípios de cada turno, com brancos e nulos do detalhe da votação.

    O nulo é `QT_TOTAL_VOTOS_NULOS`, que inclui os nulos técnicos.
    """
    municipios: dict[Chave, _Municipio] = {}
    for linha in _linhas(votos):
        total = int(linha["QT_VOTOS_NOMINAIS_VALIDOS"])
        municipio = _municipio(municipios, linha)
        numero = int(linha["NR_CANDIDATO"])
        municipio.votos[numero] = municipio.votos.get(numero, 0) + total
    for linha in _linhas(detalhe):
        municipio = _municipio(municipios, linha)
        municipio.branco += int(linha["QT_VOTOS_BRANCOS"])
        municipio.nulo += int(linha["QT_TOTAL_VOTOS_NULOS"])
    por_turno: dict[int, list[MunicipalPlace]] = {}
    for (turno, uf, codigo), municipio in sorted(municipios.items()):
        lugar = _lugar(uf, codigo, municipio)
        if lugar is not None:
            por_turno.setdefault(turno, []).append(lugar)
    return {turno: tuple(lugares) for turno, lugares in por_turno.items()}


def _municipio(municipios: dict[Chave, _Municipio], linha: dict[str, str]) -> _Municipio:
    chave = (int(linha["NR_TURNO"]), linha["SG_UF"], linha["CD_MUNICIPIO"])
    municipio = municipios.get(chave)
    if municipio is None:
        municipio = _Municipio(linha["NM_MUNICIPIO"])
        municipios[chave] = municipio
    return municipio


def _lugar(uf: str, codigo: str, municipio: _Municipio) -> MunicipalPlace | None:
    parties = tuple(
        PartyTally(numero, total, 0)
        for numero, total in sorted(municipio.votos.items())
        if total > 0
    )
    if not parties:
        return None
    tally = CargoTally(parties, municipio.branco, municipio.nulo)
    return MunicipalPlace(uf, codigo, municipio.nome, tally, None)


def _linhas(path: Path) -> Iterator[dict[str, str]]:
    try:
        archive = ZipFile(path)
    except (OSError, BadZipFile) as exc:
        raise ArchiveUnreadableError(str(path)) from exc
    with archive:
        membro = _membro(archive, path)
        with archive.open(membro) as bruto:
            texto = io.TextIOWrapper(bruto, encoding=_CODIFICACAO, newline="")
            for linha in csv.DictReader(texto, delimiter=_SEPARADOR):
                if linha["CD_CARGO"] == CARGO_PRESIDENTE:
                    yield linha


def _membro(archive: ZipFile, path: Path) -> str:
    for nome in archive.namelist():
        if nome.endswith(_SUFIXO_DO_MEMBRO):
            return nome
    raise MunzonaMemberMissingError(str(path))
