"""Conta as seções do indice-urnas.csv por turno e UF, numa só passada.

O índice tem dezenas de milhões de linhas e cresce enquanto o download roda.
A leitura é em bytes, sem o módulo csv: nenhum campo do índice tem vírgula.
Uma última linha incompleta, ainda sendo gravada, é ignorada.
"""

from pathlib import Path
from typing import Final

from eleicoes.domain.errors import ElectionError
from eleicoes.domain.votos_por_estado import ContagemIndice, SecoesIndice

_HEADER: Final = b"conjunto,turno,uf,municipio,zona,secao,arquivo,caminho,situacao,tamanho_bytes"
_FIELDS: Final = 10
_BOLETIM: Final = b"-bu.dat"
# "ignorado" é o arquivo que já estava no disco quando o download passou de novo.
_NO_DISCO: Final = frozenset({b"baixado", b"ignorado"})
_CHUNK: Final = 1 << 20


class UrnaIndexMismatchError(ElectionError):
    def __init__(self, caminho: Path) -> None:
        self.caminho = caminho
        super().__init__(f"unexpected urn index header: {caminho}")


class UrnaIndexMissingError(ElectionError):
    def __init__(self, caminho: Path) -> None:
        self.caminho = caminho
        super().__init__(f"missing urn index: {caminho}")


def contar_secoes(caminho: Path) -> ContagemIndice:
    """Seções listadas e com boletim (`*-bu.dat`) no disco, por (turno, UF).

    Marcadores `.ausente` de outros arquivos da seção, como a imagem do boletim,
    não tiram a seção da conta."""
    listadas: dict[tuple[int, bytes], set[bytes]] = {}
    com_boletim: dict[tuple[int, bytes], set[bytes]] = {}
    try:
        handle = caminho.open("rb", buffering=_CHUNK)
    except FileNotFoundError as exc:
        raise UrnaIndexMissingError(caminho) from exc
    with handle:
        if handle.readline().rstrip(b"\r\n") != _HEADER:
            raise UrnaIndexMismatchError(caminho)
        for line in handle:
            if not line.endswith(b"\n"):
                break
            campos = line.rstrip(b"\r\n").split(b",")
            if len(campos) != _FIELDS or not campos[5] or not campos[1].isdigit():
                continue
            chave = (int(campos[1]), campos[2])
            # Município, zona e seção têm largura fixa: a concatenação não colide.
            secao = campos[3] + campos[4] + campos[5]
            listadas.setdefault(chave, set()).add(secao)
            if campos[6].endswith(_BOLETIM) and campos[8] in _NO_DISCO:
                com_boletim.setdefault(chave, set()).add(secao)
    return {
        (turno, uf.decode("ascii")): SecoesIndice(
            len(secoes), len(com_boletim.get((turno, uf), ()))
        )
        for (turno, uf), secoes in sorted(listadas.items())
    }
