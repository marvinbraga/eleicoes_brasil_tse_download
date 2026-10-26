"""Lê o log da urna (log.jez) e resume os eventos de um dia de votação.

O .jez é um zip com logd.dat em latin-1, uma linha por evento, separada por tabulação:
data e hora, nível, número interno da urna, módulo, descrição e resumo. Quando a urna é
trocada durante a votação, o zip também traz, aninhado, o .jez da urna anterior.
"""

import io
import zipfile
from collections.abc import Iterator
from typing import Final

from eleicoes.domain.errors import InvalidBoletimContentError
from eleicoes.domain.integridade_urna import CARGOS_NO_LOG, ResumoLog

_ZIP: Final = b"PK"
_COMPUTADO: Final = "O voto do eleitor foi computado"
_CONFIRMADO: Final = "Voto confirmado para "
_ATRIBUIDO: Final = "Atribuido voto"
_COLUNAS: Final = 5
# Eventos depois dos quais a votação em curso recomeça do zero.
_RECOMECO: Final = frozenset(
    {"Eleitor foi habilitado", "Urna desligada pela chave", "Votação suspensa"}
)


def resumo_do_log(payload: bytes, dia: str) -> ResumoLog:
    """``dia`` no formato do log, dd/mm/aaaa.

    Um voto de cargo só conta quando a votação do eleitor termina em "voto computado".
    Se a urna é desligada no meio, ou o eleitor é habilitado de novo, o que ele já tinha
    confirmado é descartado, como a urna faz.
    """
    computados = 0
    urnas: set[str] = set()
    votos = dict.fromkeys(CARGOS_NO_LOG, 0)
    rotulos = {f"[{rotulo}]": cargo for cargo, rotulo in CARGOS_NO_LOG.items()}
    logs = 0
    for texto in _textos(payload):
        logs += 1
        pendentes: dict[str, int] = {}
        for linha in texto.splitlines():
            colunas = linha.split("\t")
            if len(colunas) < _COLUNAS or not colunas[0].startswith(dia):
                continue
            urnas.add(colunas[2])
            evento = colunas[4]
            if evento == _COMPUTADO:
                computados += 1
                for cargo, total in pendentes.items():
                    votos[cargo] += total
                pendentes = {}
            elif evento in _RECOMECO:
                pendentes = {}
            elif evento.startswith((_CONFIRMADO, _ATRIBUIDO)):
                votado = _cargo(evento, rotulos)
                if votado is not None:
                    pendentes[votado] = pendentes.get(votado, 0) + 1
    return ResumoLog(computados, votos, frozenset(urnas), logs)


def dia_do_boletim(data_hora: str) -> str:
    """'20261025T150214' do BU vira '25/10/2026', como o log escreve."""
    if len(data_hora) < 8 or not data_hora[:8].isdigit():
        raise InvalidBoletimContentError("data_hora_emissao")
    return f"{data_hora[6:8]}/{data_hora[4:6]}/{data_hora[0:4]}"


def _cargo(evento: str, rotulos: dict[str, str]) -> str | None:
    for rotulo, cargo in rotulos.items():
        if evento.endswith(rotulo):
            return cargo
    return None


def _textos(payload: bytes) -> Iterator[str]:
    try:
        arquivo = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise InvalidBoletimContentError("log") from exc
    with arquivo:
        for nome in arquivo.namelist():
            dado = arquivo.read(nome)
            if dado[:2] == _ZIP:
                yield from _textos(dado)
            else:
                yield dado.decode("latin-1")
