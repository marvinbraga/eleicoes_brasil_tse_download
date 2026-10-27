"""Signature check of one real AC section, and what each kind of tampering looks like."""

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

import pytest

from eleicoes.adapters.asn1.assinatura_reader import Asn1AssinaturaReader, autoridades
from eleicoes.adapters.curvas_urna import verificar_assinatura
from eleicoes.domain.assinatura_urna import (
    CADEIA_AC_VENCIDA,
    CADEIA_EMISSOR_DESCONHECIDO,
    CADEIA_INVALIDA,
    CADEIA_OK,
    DIVERGE,
    VALIDA,
    ArquivoNoDisco,
    Certificado,
    ConferenciaAssinatura,
    PacoteAssinaturas,
    conferir_assinaturas,
    numero_da_urna,
    sha512,
)

_PASTA = Path(__file__).resolve().parents[1] / "fixtures" / "boletins"
_NOME = "o03220ac0110400050028"
_URNA = 2295748


@pytest.fixture(scope="module")
def pacote() -> PacoteAssinaturas:
    return Asn1AssinaturaReader().read((_PASTA / f"{_NOME}-vota.vsc").read_bytes())


def _disco(*tipos: str, trocar: Mapping[str, bytes] | None = None) -> list[ArquivoNoDisco]:
    found = []
    for tipo in tipos:
        nome = f"{_NOME}-{tipo}"
        conteudo = (trocar or {}).get(tipo) or (_PASTA / nome).read_bytes()
        found.append(ArquivoNoDisco(nome, len(conteudo), sha512(conteudo)))
    return found


def _conferir(
    pacote: PacoteAssinaturas,
    no_disco: list[ArquivoNoDisco] | None = None,
    urna: int | None = _URNA,
    acs: Mapping[str, Certificado] | None = None,
) -> ConferenciaAssinatura:
    return conferir_assinaturas(
        pacote,
        _disco("bu.dat", "rdv.dat") if no_disco is None else no_disco,
        _NOME,
        urna,
        autoridades() if acs is None else acs,
        verificar_assinatura,
    )


def test_real_section_is_valid_with_the_chain_up_to_ac_ue2022(pacote: PacoteAssinaturas) -> None:
    conferencia = _conferir(pacote)

    assert conferencia.situacao == VALIDA
    assert conferencia.divergencias == ()
    assert conferencia.cadeia == CADEIA_OK
    assert conferencia.algoritmo == "ed521"
    assert conferencia.emissor == "AC UE2022"
    assert conferencia.urna == "UEAO02295748"
    assert len(conferencia.conferidos) == 2
    # log, imagem do BU, biometria e outros que a urna lista e não estão no disco
    assert conferencia.nao_baixados == len(pacote.hardware.arquivos) - 2


def test_changed_file_breaks_the_hash(pacote: PacoteAssinaturas) -> None:
    rdv = bytearray((_PASTA / f"{_NOME}-rdv.dat").read_bytes())
    rdv[100] ^= 1
    conferencia = _conferir(pacote, _disco("bu.dat", "rdv.dat", trocar={"rdv.dat": bytes(rdv)}))

    assert conferencia.situacao == DIVERGE
    assert conferencia.divergencias == ("hash_difere:rdv.dat",)


def test_extra_or_truncated_files_diverge(pacote: PacoteAssinaturas) -> None:
    curto = (_PASTA / f"{_NOME}-bu.dat").read_bytes()[:-1]
    estranho = ArquivoNoDisco(f"{_NOME}-extra.dat", 1, sha512(b"x"))
    conferencia = _conferir(pacote, [*_disco("bu.dat", trocar={"bu.dat": curto}), estranho])

    assert "tamanho_difere:bu.dat" in conferencia.divergencias
    assert "hash_difere:bu.dat" in conferencia.divergencias
    assert "fora_da_lista:extra.dat" in conferencia.divergencias


def test_forged_list_breaks_the_hardware_signature(pacote: PacoteAssinaturas) -> None:
    hardware = pacote.hardware
    primeiro = replace(hardware.arquivos[0], resumo=sha512(b"outro boletim"))
    forjado = replace(hardware, arquivos=(primeiro, *hardware.arquivos[1:]))
    conferencia = _conferir(replace(pacote, hardware=forjado), [])

    assert "listas_sw_hw_diferem" in conferencia.divergencias


def test_signatures_are_checked_against_the_key(pacote: PacoteAssinaturas) -> None:
    hardware = pacote.hardware
    assinatura = bytearray(hardware.assinatura_conteudo)
    assinatura[10] ^= 1
    primeiro = replace(hardware.arquivos[0], assinatura=bytes(132))
    alterado = replace(
        hardware,
        assinatura_conteudo=bytes(assinatura),
        arquivos=(primeiro, *hardware.arquivos[1:]),
    )
    conferencia = _conferir(replace(pacote, hardware=alterado))

    assert "assinatura_da_lista_invalida" in conferencia.divergencias
    assert "assinatura_invalida:bu.dat" in conferencia.divergencias


def test_changed_list_content_and_other_section_names(pacote: PacoteAssinaturas) -> None:
    software = replace(pacote.software, conteudo=pacote.software.conteudo + b"\x00")
    outro = replace(pacote.hardware.arquivos[0], nome="o03220ac0110400050029-bu.dat")
    hardware = replace(pacote.hardware, arquivos=(outro, *pacote.hardware.arquivos[1:]))
    conferencia = _conferir(replace(pacote, software=software, hardware=hardware), [])

    assert "lista_sw_alterada" in conferencia.divergencias
    assert "lista_de_outra_secao" in conferencia.divergencias


def test_certificate_must_be_the_bu_urn(pacote: PacoteAssinaturas) -> None:
    assert _conferir(pacote, urna=_URNA + 1).divergencias == ("urna_difere_do_bu",)
    assert _conferir(pacote, urna=None).situacao == VALIDA
    trocado = replace(pacote.hardware, usuario="ueao00000001")
    conferencia = _conferir(replace(pacote, hardware=trocado))
    assert conferencia.divergencias == ("assinante_difere_do_certificado",)


def test_chain_states(pacote: PacoteAssinaturas) -> None:
    acs = dict(autoridades())
    ac = acs["AC UE2022"]

    assert _conferir(pacote, acs={}).cadeia == CADEIA_EMISSOR_DESCONHECIDO
    vencida = {"AC UE2022": replace(ac, fim="20260101T000000")}
    assert _conferir(pacote, acs=vencida).cadeia == CADEIA_AC_VENCIDA
    assert _conferir(pacote, acs=vencida).situacao == VALIDA
    outra_chave = {"AC UE2022": replace(ac, chave=acs["AC UE2020"].chave, identificador=None)}
    conferencia = _conferir(pacote, acs=outra_chave)
    assert conferencia.cadeia == CADEIA_INVALIDA
    assert "cadeia_invalida" in conferencia.divergencias
    outro_id = {"AC UE2022": replace(ac, identificador=b"\x00" * 20)}
    assert _conferir(pacote, acs=outro_id).cadeia == CADEIA_INVALIDA
    outro_algoritmo = {"AC UE2022": replace(ac, algoritmo_chave="ecdsa_p521")}
    assert _conferir(pacote, acs=outro_algoritmo).cadeia == CADEIA_INVALIDA


def test_certificate_validity_and_algorithm(pacote: PacoteAssinaturas) -> None:
    certificado = replace(pacote.certificado, fim="20260101T000000")
    conferencia = _conferir(replace(pacote, certificado=certificado))
    assert "certificado_fora_da_validade" in conferencia.divergencias

    hardware = replace(pacote.hardware, algoritmo=2)
    conferencia = _conferir(replace(pacote, hardware=hardware))
    assert conferencia.divergencias[0] == "algoritmo_difere_do_certificado"


def test_urn_number_comes_from_the_digits() -> None:
    assert numero_da_urna("UEAO02468149") == 2468149
    assert numero_da_urna("ueao01813372") == 1813372
    assert numero_da_urna("UEAO") is None
