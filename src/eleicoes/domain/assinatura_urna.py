"""Conferência da assinatura digital dos arquivos de uma urna (o arquivo vota.vsc).

A urna lista, para cada arquivo que grava (BU, RDV, log, imagem do BU e outros que o TSE não
publica), o tamanho, o SHA-512 e duas assinaturas: uma de software (CEPESC, algoritmo
proprietário, sem verificação pública) e uma de hardware, feita pelo chip de segurança da
urna com a chave do certificado que vai no próprio arquivo. A conferência, para cada seção:

* o SHA-512 e o tamanho de cada arquivo baixado batem com a lista da urna, e as listas de
  software e de hardware são iguais;
* a lista de hardware tem o hash certo e está assinada pela chave do certificado;
* cada arquivo baixado tem a assinatura de hardware válida;
* o certificado é da urna do BU e foi assinado por uma AC conhecida do TSE, dentro da validade.

A cadeia é conferida até a AC que emite os certificados das urnas (AC URNA, AC UE2020,
AC UE2022). Os certificados raiz acima delas não são públicos, e a revogação não é consultada.
"""

import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final, Protocol

VALIDA: Final = "valida"
DIVERGE: Final = "diverge"

ED521: Final = "ed521"
ECDSA_P521: Final = "ecdsa_p521"
# Códigos de AlgoritmoAssinatura na especificação do TSE.
ALGORITMOS: Final[Mapping[int, str]] = {2: ECDSA_P521, 4: ED521}

# Situação da cadeia do certificado da urna.
CADEIA_OK: Final = "verificada"
CADEIA_AC_VENCIDA: Final = "ac_vencida"
CADEIA_EMISSOR_DESCONHECIDO: Final = "emissor_desconhecido"
CADEIA_INVALIDA: Final = "invalida"


@dataclass(frozen=True, slots=True)
class Certificado:
    """Os campos de um certificado X.509 que a conferência usa. Datas em AAAAMMDDThhmmss."""

    sujeito: str
    emissor: str
    inicio: str
    fim: str
    algoritmo_chave: str
    chave: bytes
    algoritmo_assinatura: str
    tbs: bytes
    assinatura: bytes
    identificador: bytes | None = None
    identificador_emissor: bytes | None = None


@dataclass(frozen=True, slots=True)
class ArquivoAssinado:
    nome: str
    tamanho: int
    resumo: bytes
    assinatura: bytes


@dataclass(frozen=True, slots=True)
class Envelope:
    """Uma EntidadeAssinatura: a lista de arquivos e a assinatura da própria lista."""

    data_hora: str
    usuario: str
    serial: int
    algoritmo: int
    conteudo: bytes
    resumo_conteudo: bytes
    assinatura_conteudo: bytes
    arquivos: tuple[ArquivoAssinado, ...]


@dataclass(frozen=True, slots=True)
class PacoteAssinaturas:
    modelo: int
    software: Envelope
    hardware: Envelope
    certificado: Certificado


@dataclass(frozen=True, slots=True)
class ArquivoNoDisco:
    nome: str
    tamanho: int
    resumo: bytes


class Verificador(Protocol):
    def __call__(self, algoritmo: str, chave: bytes, mensagem: bytes, assinatura: bytes) -> bool:
        """mensagem é o que entra no algoritmo: o texto no Ed521, o resumo SHA-512 no ECDSA."""
        ...


@dataclass(frozen=True, slots=True)
class ConferenciaAssinatura:
    situacao: str
    modelo: int
    algoritmo: str
    urna: str
    emissor: str
    cadeia: str
    conferidos: tuple[str, ...]
    nao_baixados: int
    divergencias: tuple[str, ...] = ()
    detalhes: Mapping[str, str] = field(default_factory=dict)
    # Assinado pela urna que rodou o Recuperador de Dados, não pela urna do BU.
    recuperada: bool = False


def sha512(conteudo: bytes) -> bytes:
    return hashlib.sha512(conteudo).digest()


def numero_da_urna(texto: str) -> int | None:
    """ "UEAO02468149" e "ueao01813372" trazem o número interno da urna nos dígitos."""
    digitos = re.sub(r"\D", "", texto)
    return int(digitos) if digitos else None


def conferir_assinaturas(
    pacote: PacoteAssinaturas,
    no_disco: Sequence[ArquivoNoDisco],
    prefixo: str,
    numero_interno_urna: int | None,
    autoridades: Mapping[str, Certificado],
    verificar: Verificador,
    recuperadoras: frozenset[int] = frozenset(),
) -> ConferenciaAssinatura:
    """recuperadoras: urnas que, pelo log do pacote, geraram os arquivos de resultado."""
    divergencias: list[str] = []
    detalhes: dict[str, str] = {}
    hardware = pacote.hardware
    certificado = pacote.certificado
    algoritmo = ALGORITMOS.get(hardware.algoritmo, f"desconhecido:{hardware.algoritmo}")
    if algoritmo != certificado.algoritmo_chave:
        divergencias.append("algoritmo_difere_do_certificado")
    divergencias.extend(_contra_lista(pacote, prefixo))
    divergencias.extend(_contra_disco(pacote, no_disco, detalhes))
    divergencias.extend(_contra_urna(pacote, numero_interno_urna, recuperadoras, detalhes))
    divergencias.extend(_assinaturas(pacote, no_disco, verificar))
    cadeia = _cadeia(certificado, hardware.data_hora, autoridades, verificar, detalhes)
    if cadeia in (CADEIA_INVALIDA, CADEIA_EMISSOR_DESCONHECIDO):
        divergencias.append(f"cadeia_{cadeia}")
    if not certificado.inicio <= hardware.data_hora <= certificado.fim:
        divergencias.append("certificado_fora_da_validade")
        detalhes["validade"] = (
            f"{certificado.inicio} a {certificado.fim}, assinado {hardware.data_hora}"
        )
    nomes_no_disco = {arquivo.nome for arquivo in no_disco}
    return ConferenciaAssinatura(
        DIVERGE if divergencias else VALIDA,
        pacote.modelo,
        algoritmo,
        certificado.sujeito,
        certificado.emissor,
        cadeia,
        tuple(sorted(nomes_no_disco)),
        sum(1 for item in hardware.arquivos if item.nome not in nomes_no_disco),
        tuple(divergencias),
        detalhes,
        _recuperada(pacote, numero_interno_urna, recuperadoras),
    )


def _contra_lista(pacote: PacoteAssinaturas, prefixo: str) -> list[str]:
    found: list[str] = []
    for envelope, nome in ((pacote.software, "sw"), (pacote.hardware, "hw")):
        if sha512(envelope.conteudo) != envelope.resumo_conteudo:
            found.append(f"lista_{nome}_alterada")
    if _chaves(pacote.software) != _chaves(pacote.hardware):
        found.append("listas_sw_hw_diferem")
    if any(not item.nome.startswith(f"{prefixo}-") for item in pacote.hardware.arquivos):
        found.append("lista_de_outra_secao")
    return found


def _chaves(envelope: Envelope) -> set[tuple[str, int, bytes]]:
    return {(item.nome, item.tamanho, item.resumo) for item in envelope.arquivos}


def _contra_disco(
    pacote: PacoteAssinaturas, no_disco: Sequence[ArquivoNoDisco], detalhes: dict[str, str]
) -> list[str]:
    listados = {item.nome: item for item in pacote.hardware.arquivos}
    found: list[str] = []
    for arquivo in no_disco:
        assinado = listados.get(arquivo.nome)
        if assinado is None:
            found.append(f"fora_da_lista:{_tipo(arquivo.nome)}")
            continue
        if assinado.tamanho != arquivo.tamanho:
            found.append(f"tamanho_difere:{_tipo(arquivo.nome)}")
            detalhes[_tipo(arquivo.nome)] = f"lista {assinado.tamanho} | disco {arquivo.tamanho}"
        if assinado.resumo != arquivo.resumo:
            found.append(f"hash_difere:{_tipo(arquivo.nome)}")
    return found


def _recuperada(
    pacote: PacoteAssinaturas, numero_interno_urna: int | None, recuperadoras: frozenset[int]
) -> bool:
    do_certificado = numero_da_urna(pacote.certificado.sujeito)
    return numero_interno_urna not in (None, do_certificado) and do_certificado in recuperadoras


def _contra_urna(
    pacote: PacoteAssinaturas,
    numero_interno_urna: int | None,
    recuperadoras: frozenset[int],
    detalhes: dict[str, str],
) -> list[str]:
    do_certificado = numero_da_urna(pacote.certificado.sujeito)
    do_usuario = numero_da_urna(pacote.hardware.usuario) or pacote.hardware.serial
    if do_certificado != do_usuario:
        detalhes["urna"] = f"certificado {do_certificado} | assinante {do_usuario}"
        return ["assinante_difere_do_certificado"]
    if numero_interno_urna is not None and do_certificado != numero_interno_urna:
        detalhes["urna"] = f"certificado {do_certificado} | BU {numero_interno_urna}"
        if do_certificado in recuperadoras:
            detalhes["urna"] += " | o log mostra a recuperação dos dados nessa urna"
            return []
        return ["urna_difere_do_bu"]
    return []


def _assinaturas(
    pacote: PacoteAssinaturas, no_disco: Sequence[ArquivoNoDisco], verificar: Verificador
) -> list[str]:
    """A da lista cobre o hash de todos; a de cada arquivo baixado é conferida também."""
    hardware = pacote.hardware
    algoritmo = pacote.certificado.algoritmo_chave
    chave = pacote.certificado.chave
    found: list[str] = []
    if not verificar(
        algoritmo, chave, sha512(hardware.resumo_conteudo), hardware.assinatura_conteudo
    ):
        found.append("assinatura_da_lista_invalida")
    listados = {item.nome: item for item in hardware.arquivos}
    for arquivo in no_disco:
        assinado = listados.get(arquivo.nome)
        if assinado is None:
            continue
        if not verificar(algoritmo, chave, sha512(assinado.resumo), assinado.assinatura):
            found.append(f"assinatura_invalida:{_tipo(arquivo.nome)}")
    return found


def _cadeia(
    certificado: Certificado,
    data_hora: str,
    autoridades: Mapping[str, Certificado],
    verificar: Verificador,
    detalhes: dict[str, str],
) -> str:
    autoridade = autoridades.get(certificado.emissor)
    if autoridade is None:
        detalhes["cadeia"] = f"emissor {certificado.emissor} fora da lista de ACs do TSE"
        return CADEIA_EMISSOR_DESCONHECIDO
    if (
        certificado.identificador_emissor is not None
        and autoridade.identificador is not None
        and certificado.identificador_emissor != autoridade.identificador
    ):
        detalhes["cadeia"] = "identificador da chave do emissor difere"
        return CADEIA_INVALIDA
    if certificado.algoritmo_assinatura != autoridade.algoritmo_chave:
        detalhes["cadeia"] = "algoritmo da assinatura do certificado difere da chave da AC"
        return CADEIA_INVALIDA
    mensagem = certificado.tbs if autoridade.algoritmo_chave == ED521 else sha512(certificado.tbs)
    if not verificar(
        autoridade.algoritmo_chave, autoridade.chave, mensagem, certificado.assinatura
    ):
        detalhes["cadeia"] = f"assinatura da {autoridade.sujeito} no certificado não confere"
        return CADEIA_INVALIDA
    if not autoridade.inicio <= data_hora <= autoridade.fim:
        detalhes["cadeia"] = f"{autoridade.sujeito} válida até {autoridade.fim}"
        return CADEIA_AC_VENCIDA
    return CADEIA_OK


def _tipo(nome: str) -> str:
    """ "o03220ac0100700090001-bu.dat" → "bu.dat"."""
    return nome.split("-", 1)[-1]
