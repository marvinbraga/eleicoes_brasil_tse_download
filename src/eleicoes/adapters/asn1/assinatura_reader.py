"""Decodifica o vota.vsc (assinaturas da urna) e os certificados X.509 que ele carrega."""

import base64
import re
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Final, cast

from eleicoes.domain.assinatura_urna import (
    ECDSA_P521,
    ED521,
    ArquivoAssinado,
    Certificado,
    Envelope,
    PacoteAssinaturas,
)
from eleicoes.domain.errors import InvalidSignatureFileError

_PASTA: Final = Path(__file__).resolve().parent
_SPEC: Final = _PASTA / "assinatura.asn1"
_AUTORIDADES: Final = _PASTA / "autoridades_urna.pem"
_ENTIDADE: Final = "EntidadeAssinaturaEcourna2026"

# OIDs já codificados (conteúdo do OBJECT IDENTIFIER, sem etiqueta e comprimento).
_OID_ED521: Final = bytes.fromhex("2b0601040182dc2c0201")  # 1.3.6.1.4.1.44588.2.1
_OID_EC_PUBLICA: Final = bytes.fromhex("2a8648ce3d0201")  # 1.2.840.10045.2.1
_OID_P521: Final = bytes.fromhex("2b81040023")  # 1.3.132.0.35
_OID_ECDSA_SHA512: Final = bytes.fromhex("2a8648ce3d040304")  # 1.2.840.10045.4.3.4
_OID_NOME_COMUM: Final = bytes.fromhex("550403")  # 2.5.4.3
_OID_ID_CHAVE: Final = bytes.fromhex("551d0e")  # 2.5.29.14
_OID_ID_CHAVE_EMISSOR: Final = bytes.fromhex("551d23")  # 2.5.29.35
_PEM: Final = re.compile(rb"-----BEGIN CERTIFICATE-----(.+?)-----END CERTIFICATE-----", re.S)


class Asn1AssinaturaReader:
    def __init__(self) -> None:
        import asn1tools

        self._spec = asn1tools.compile_files(str(_SPEC), codec="ber", numeric_enums=True)

    def read(self, payload: bytes) -> PacoteAssinaturas:
        try:
            raw = cast(Mapping[str, object], self._spec.decode(_ENTIDADE, payload))
            software = self._envelope(_mapa(raw["assinaturaSW"]))
            hardware_raw = _mapa(raw["assinaturaHW"])
            hardware = self._envelope(hardware_raw)
            modelo = int(cast(int, _mapa(raw["equipamento"])["modeloEquipamento"]))
            certificado = ler_certificado(cast(bytes, hardware_raw["certificadoDigital"]))
        except InvalidSignatureFileError:
            raise
        except Exception as exc:
            raise InvalidSignatureFileError("vsc") from exc
        return PacoteAssinaturas(modelo, software, hardware, certificado)

    def _envelope(self, raw: Mapping[str, object]) -> Envelope:
        auto = _mapa(raw["autoAssinado"])
        usuario = _mapa(auto["usuario"])
        assinatura = _mapa(auto["assinatura"])
        conteudo = bytes(cast(bytes, raw["conteudoAutoAssinado"]))
        lista = _mapa(self._spec.decode("Assinatura", conteudo))
        arquivos = tuple(
            _arquivo(_mapa(item)) for item in cast(list[object], lista["arquivosAssinados"])
        )
        return Envelope(
            str(raw["dataHoraCriacao"]),
            str(usuario["nomeUsuario"]),
            int(cast(int, usuario["serial"])),
            int(cast(int, _mapa(auto["algoritmoAssinatura"])["algoritmo"])),
            conteudo,
            bytes(cast(bytes, assinatura["hash"])),
            bytes(cast(bytes, assinatura["assinatura"])),
            arquivos,
        )


def _arquivo(raw: Mapping[str, object]) -> ArquivoAssinado:
    assinatura = _mapa(raw["assinatura"])
    return ArquivoAssinado(
        str(raw["nomeArquivo"]),
        int(cast(int, assinatura["tamanho"])),
        bytes(cast(bytes, assinatura["hash"])),
        bytes(cast(bytes, assinatura["assinatura"])),
    )


def _mapa(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise InvalidSignatureFileError("vsc")
    return cast(Mapping[str, object], value)


@lru_cache(maxsize=1)
def autoridades() -> Mapping[str, Certificado]:
    """As ACs do TSE que emitem certificados de urna, pelo nome comum."""
    pems = _PEM.findall(_AUTORIDADES.read_bytes())
    return {cert.sujeito: cert for cert in (ler_certificado(_der(pem)) for pem in pems)}


def ler_certificado(dados: bytes) -> Certificado:
    """Aceita PEM (UE2020 e UE2022) ou DER (modelos antigos)."""
    try:
        return _certificado(_der(dados) if dados.lstrip().startswith(b"-----") else dados)
    except (IndexError, ValueError) as exc:
        raise InvalidSignatureFileError("certificado") from exc


def _der(pem: bytes) -> bytes:
    corpo = _PEM.search(pem)
    texto = pem if corpo is None else corpo.group(1)
    return base64.b64decode(b"".join(texto.split()), validate=True)


# --- DER ---------------------------------------------------------------------------------------

_Tlv = tuple[int, int, int, int]  # (etiqueta, início do TLV, início do valor, fim)


def _tlv(der: bytes, inicio: int) -> _Tlv:
    etiqueta = der[inicio]
    comprimento = der[inicio + 1]
    valor = inicio + 2
    if comprimento & 0x80:
        bytes_comprimento = comprimento & 0x7F
        if not 0 < bytes_comprimento <= 3:
            raise ValueError("comprimento DER")
        comprimento = int.from_bytes(der[valor : valor + bytes_comprimento], "big")
        valor += bytes_comprimento
    fim = valor + comprimento
    if fim > len(der):
        raise ValueError("DER truncado")
    return etiqueta, inicio, valor, fim


def _filhos(der: bytes, pai: _Tlv) -> list[_Tlv]:
    found: list[_Tlv] = []
    posicao = pai[2]
    while posicao < pai[3]:
        filho = _tlv(der, posicao)
        found.append(filho)
        posicao = filho[3]
    if posicao != pai[3]:
        raise ValueError("DER desalinhado")
    return found


def _valor(der: bytes, tlv: _Tlv) -> bytes:
    return der[tlv[2] : tlv[3]]


def _certificado(der: bytes) -> Certificado:
    raiz = _tlv(der, 0)
    # Parte das urnas UE2013/UE2015 grava o DER seguido de um byte zero; o script do TSE lê
    # com o OpenSSL, que ignora a sobra. Só zeros são aceitos depois do certificado.
    if der[raiz[3] :].strip(b"\x00"):
        raise ValueError("bytes após o certificado")
    tbs, algoritmo_assinatura, bits_assinatura = _filhos(der, raiz)
    campos = _filhos(der, tbs)
    if campos[0][0] == 0xA0:  # versão explícita
        campos = campos[1:]
    _serie, _algoritmo, emissor, validade, sujeito, chave_publica = campos[:6]
    extensoes = next((item for item in campos[6:] if item[0] == 0xA3), None)
    inicio, fim = (_data(der, item) for item in _filhos(der, validade))
    algoritmo_chave, chave = _chave_publica(der, chave_publica)
    identificador, identificador_emissor = _identificadores(der, extensoes)
    assinatura = _valor(der, bits_assinatura)
    if not assinatura or assinatura[0] != 0:
        raise ValueError("BIT STRING com bits sobrando")
    return Certificado(
        sujeito=_nome_comum(der, sujeito),
        emissor=_nome_comum(der, emissor),
        inicio=inicio,
        fim=fim,
        algoritmo_chave=algoritmo_chave,
        chave=chave,
        algoritmo_assinatura=_algoritmo_assinatura(der, algoritmo_assinatura),
        tbs=der[tbs[1] : tbs[3]],
        assinatura=assinatura[1:],
        identificador=identificador,
        identificador_emissor=identificador_emissor,
    )


def _nome_comum(der: bytes, nome: _Tlv) -> str:
    for conjunto in _filhos(der, nome):
        for atributo in _filhos(der, conjunto):
            tipo, valor = _filhos(der, atributo)
            if _valor(der, tipo) == _OID_NOME_COMUM:
                return _valor(der, valor).decode("utf-8")
    raise ValueError("certificado sem nome comum")


def _data(der: bytes, tempo: _Tlv) -> str:
    """UTCTime (AAMMDDhhmmssZ) ou GeneralizedTime (AAAAMMDDhhmmssZ) → AAAAMMDDThhmmss."""
    texto = _valor(der, tempo).decode("ascii").rstrip("Z")
    if tempo[0] == 0x17:
        ano = int(texto[:2])
        texto = f"{1900 + ano if ano >= 50 else 2000 + ano}{texto[2:]}"
    return f"{texto[:8]}T{texto[8:14]}"


def _chave_publica(der: bytes, info: _Tlv) -> tuple[str, bytes]:
    algoritmo, bits = _filhos(der, info)
    partes = _filhos(der, algoritmo)
    oid = _valor(der, partes[0])
    chave = _valor(der, bits)
    if not chave or chave[0] != 0:
        raise ValueError("BIT STRING com bits sobrando")
    if oid == _OID_ED521:
        return ED521, chave[1:]
    if oid == _OID_EC_PUBLICA and len(partes) > 1 and _valor(der, partes[1]) == _OID_P521:
        return ECDSA_P521, chave[1:]
    raise ValueError("algoritmo de chave não suportado")


def _algoritmo_assinatura(der: bytes, algoritmo: _Tlv) -> str:
    oid = _valor(der, _filhos(der, algoritmo)[0])
    if oid == _OID_ED521:
        return ED521
    if oid == _OID_ECDSA_SHA512:
        return ECDSA_P521
    raise ValueError("algoritmo de assinatura não suportado")


def _identificadores(der: bytes, extensoes: _Tlv | None) -> tuple[bytes | None, bytes | None]:
    identificador: bytes | None = None
    identificador_emissor: bytes | None = None
    if extensoes is None:
        return None, None
    (lista,) = _filhos(der, extensoes)
    for extensao in _filhos(der, lista):
        partes = _filhos(der, extensao)
        oid = _valor(der, partes[0])
        conteudo = _valor(der, partes[-1])
        if oid == _OID_ID_CHAVE:
            identificador = _valor(conteudo, _tlv(conteudo, 0))
        elif oid == _OID_ID_CHAVE_EMISSOR:
            sequencia = _tlv(conteudo, 0)
            for campo in _filhos(conteudo, sequencia):
                if campo[0] == 0x80:  # keyIdentifier [0]
                    identificador_emissor = _valor(conteudo, campo)
    return identificador, identificador_emissor
