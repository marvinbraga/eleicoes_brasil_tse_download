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
# A urna religou sem registro de desligamento: faltou energia.
_REINICIO: Final = "Início das operações do logd"
# O último cargo da cédula: confirmado ele, o voto já está gravado no RDV.
_ULTIMO_CARGO: Final = "presidente"


def resumo_do_log(payload: bytes, dia: str) -> ResumoLog:
    """``dia`` no formato do log, dd/mm/aaaa.

    Um voto de cargo só conta quando a votação do eleitor termina em "voto computado".
    Se a urna é desligada no meio, ou o eleitor é habilitado de novo, o que ele já tinha
    confirmado é descartado, como a urna faz. A urna grava o log na memória interna e na
    externa, e depois de um reinício trechos podem aparecer de novo; cada linha traz o
    próprio resumo, então linha repetida é o mesmo evento.
    """
    contagem = _Contagem()
    vistas: set[str] = set()
    for texto in _textos(payload):
        contagem.logs += 1
        contagem.pendentes = {}
        for linha in texto.splitlines():
            colunas = linha.split("\t")
            if len(colunas) < _COLUNAS or not colunas[0].startswith(dia) or linha in vistas:
                continue
            vistas.add(linha)
            contagem.evento(colunas[2], colunas[4])
    return contagem.resumo()


class _Contagem:
    def __init__(self) -> None:
        self.computados = 0
        self.interrompidos = 0
        self.logs = 0
        self.urnas: set[str] = set()
        self.votos = dict.fromkeys(CARGOS_NO_LOG, 0)
        self.por_urna: dict[str, tuple[int, dict[str, int]]] = {}
        self.pendentes: dict[str, int] = {}
        self._rotulos = {f"[{rotulo}]": cargo for cargo, rotulo in CARGOS_NO_LOG.items()}

    def evento(self, urna: str, evento: str) -> None:
        self.urnas.add(urna)
        if evento == _COMPUTADO:
            self._computar(urna)
        elif evento == _REINICIO:
            # Queda de energia logo depois do último cargo: a linha "computado" se perdeu.
            if self.pendentes.get(_ULTIMO_CARGO):
                self.interrompidos += 1
            self.pendentes = {}
        elif evento in _RECOMECO:
            self.pendentes = {}
        elif evento.startswith((_CONFIRMADO, _ATRIBUIDO)):
            votado = _cargo(evento, self._rotulos)
            if votado is not None:
                self.pendentes[votado] = self.pendentes.get(votado, 0) + 1

    def resumo(self) -> ResumoLog:
        return ResumoLog(
            self.computados,
            self.votos,
            frozenset(self.urnas),
            self.logs,
            self.por_urna,
            self.interrompidos,
        )

    def _computar(self, urna: str) -> None:
        self.computados += 1
        total, votos = self.por_urna.get(urna, (0, dict.fromkeys(CARGOS_NO_LOG, 0)))
        for cargo, quantidade in self.pendentes.items():
            self.votos[cargo] += quantidade
            votos[cargo] += quantidade
        self.por_urna[urna] = (total + 1, votos)
        self.pendentes = {}


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
