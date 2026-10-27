"""The vota.vsc reader decodes the 2026 layout and the certificates it carries."""

from pathlib import Path

import pytest

from eleicoes.adapters.asn1.assinatura_reader import (
    Asn1AssinaturaReader,
    autoridades,
    ler_certificado,
)
from eleicoes.domain.assinatura_urna import ECDSA_P521, ED521
from eleicoes.domain.errors import InvalidSignatureFileError

_PASTA = Path(__file__).resolve().parents[1] / "fixtures" / "boletins"
_NOME = "o03220ac0110400050028"


@pytest.fixture(scope="module")
def vsc() -> bytes:
    return (_PASTA / f"{_NOME}-vota.vsc").read_bytes()


def test_reads_both_envelopes_and_the_urn_certificate(vsc: bytes) -> None:
    pacote = Asn1AssinaturaReader().read(vsc)

    assert pacote.modelo == 22
    assert pacote.hardware.algoritmo == 4
    assert pacote.software.algoritmo == 3
    assert pacote.hardware.usuario == "UEAO"
    assert [item.nome.split("-", 1)[1] for item in pacote.hardware.arquivos][:2] == [
        "bu.dat",
        "rdv.dat",
    ]
    assert pacote.hardware.arquivos[0].tamanho == (_PASTA / f"{_NOME}-bu.dat").stat().st_size
    certificado = pacote.certificado
    assert certificado.sujeito == "UEAO02295748"
    assert certificado.emissor == "AC UE2022"
    assert certificado.algoritmo_chave == ED521
    assert certificado.algoritmo_assinatura == ED521
    assert len(certificado.chave) == 66
    assert len(certificado.assinatura) == 132
    assert certificado.identificador_emissor == autoridades()["AC UE2022"].identificador


def test_loads_the_three_tse_authorities() -> None:
    found = autoridades()

    assert sorted(found) == ["AC UE2020", "AC UE2022", "AC URNA"]
    assert found["AC URNA"].algoritmo_chave == ECDSA_P521
    assert found["AC URNA"].algoritmo_assinatura == ECDSA_P521
    assert found["AC URNA"].fim == "20260718T215957"
    assert found["AC UE2022"].inicio == "20230228T134649"


def test_garbage_is_reported_as_an_invalid_signature_file(vsc: bytes) -> None:
    leitor = Asn1AssinaturaReader()
    with pytest.raises(InvalidSignatureFileError):
        leitor.read(b"\x30\x03\x02\x01\x01")
    with pytest.raises(InvalidSignatureFileError):
        leitor.read(vsc[: len(vsc) // 2])


def test_broken_certificates_are_invalid() -> None:
    with pytest.raises(InvalidSignatureFileError):
        ler_certificado(b"\x30\x05\x02\x01\x01")
    with pytest.raises(InvalidSignatureFileError):
        ler_certificado(b"\x30\x84\x00\x00\x00\x01\x00")
