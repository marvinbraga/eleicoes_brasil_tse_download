"""Ed521 and ECDSA P-521 verification against published and real vectors."""

import hashlib

from eleicoes.adapters import curvas_urna as curvas
from eleicoes.domain.assinatura_urna import ECDSA_P521, ED521

# Vetores do ECPy (src/ecpy/eddsa.py), a biblioteca que o script de verificação do TSE usa.
_ED_X = int(
    "16b159d5e880d2849165dec4d95d69051129baa1f8c23b2c95284c142d122f1bb96048547b30d2f2"
    "df430d36d40190ca86b8ef266a72b3034c4d03fe83d5b1b9c4e",
    16,
)
_ED_Y = int(
    "6cd6658b0e2a6100d1487507ac3c0f1b52677b2eb31074aebd5bdede3775d3e6447f7f714d2740d0"
    "ba46e67aedcc4c3f37410c47a26cf79077dbc3f9cb0c8700fb",
    16,
)
_ED_PRIVADA = int(
    "a0d4d2ea5090b09a5d05ddf8c10d72e3a4b5c435fbff6d3a5f775cfe837f158fcf4e04b3d70713b7"
    "1e834f3bec2442ef4c5c8a1ffb6f2f81dec330226ffe2f46a285",
    16,
)
_ED_ASSINATURA = bytes.fromhex(
    "c2fb4f7d03dd31f25753b9972aeb650ac3632eef945e7f94e426a865bb95e66241149c7eed24d98f"
    "ed2ee8b9ef949b83ba556d045b72df6e6b8b9026414b26463d0088d2ed5ea88fcc6b2f343d308209"
    "dacd5fadadac352d497d2049831eca3536e7be5a7faef56d6c6786c60415e0febee8a45f9971ae48"
    "72e0b6cf09cc0a9407342000"
)
_ED_MENSAGEM = b"Message for Ed521 signing"

_X509_X = int(
    "23edddd64369863618296219add6d6dcafae3cc8e5666a6b6a1fea1d9cf92552c6836f51bfb87288"
    "4cde1cc45837f7390b47f7e7e4c9722327ba09b5a97a88028",
    16,
)
_X509_Y = int(
    "12ce0b0c0eeac8418dc8639f628c183ed1523b2c71d4090f8e5c44c90e07cbaceb17ef077af8e120"
    "fb0350243780f61007cbd158de2f2d28d7295f135195afd6a9b",
    16,
)
_X509_ASSINATURA = bytes.fromhex(
    "a7e7f16597a9b70f9e6437de6e85239def223d68263cf49b3b8575e49a34d23bb79de2f3e59ecba4"
    "b5358e0eaea575b4645a6e420ff88632fe8725b0fe3ee92a510116969cba3cdc6c7b644d50efa279"
    "08dbceef807b180ec1e7e63c5badf058ea97112fbba153e3d672552c1ff49c754fdc1b891e470cfd"
    "d058fd788da6f98fa8e73200"
)
_X509_TBS = bytes.fromhex(
    "308202bfa003020102020900e4ac9a3346c92509300c060a2b0601040182dc2c0201308197310b30"
    "0906035504061302425231133011060355040a0c0a4943502d42726173696c313d303b060355040b"
    "0c34496e7374697475746f204e6163696f6e616c206465205465636e6f6c6f67696120646120496e"
    "666f726d6163616f202d204954493134303206035504030c2b4175746f72696461646520436572746"
    "966696361646f7261205261697a2042726173696c65697261207637301e170d313831323238313334"
    "3733355a170d3338313232383132303033355a308197310b30090603550406130242523113301106"
    "0355040a0c0a4943502d42726173696c313d303b060355040b0c34496e7374697475746f204e6163"
    "696f6e616c206465205465636e6f6c6f67696120646120496e666f726d6163616f202d2049544931"
    "34303206035504030c2b4175746f72696461646520436572746966696361646f7261205261697a20"
    "42726173696c656972612076373053300c060a2b0601040182dc2c02010343009b6afd5a1935f195"
    "728dd2f2e28d15bd7c00610f78430235b00f128eaf77f07eb1ceba7ce0904cc4e5f890401dc7b223"
    "15ed83c128f63986dc1884aceec0b0e02c01a381f53081f2304e0603551d200447304530430605604"
    "c010100303a303806082b06010505070201162c687474703a2f2f61637261697a2e69637062726173"
    "696c2e676f762e62722f44504361637261697a2e706466303f0603551d1f043830363034a032a0308"
    "62e687474703a2f2f61637261697a2e69637062726173696c2e676f762e62722f4c43526163726169"
    "7a76372e63726c301f0603551d2304183016801475513119e1c71321873e415fa31be67bfdb0d9c83"
    "01d0603551d0e0416041475513119e1c71321873e415fa31be67bfdb0d9c8300f0603551d130101ff"
    "040530030101ff300e0603551d0f0101ff040403020106"
)

# Assinatura real de uma urna UE2015 (seção 0002, zona 0018, município 08915, MA, 2º turno
# de 2026) sobre SHA-512 do hash do BU, conferida também com openssl pkeyutl -verify.
_ECDSA_CHAVE = bytes.fromhex(
    "0401b72806cd6b3dd033fa2ff2428a9296499808ba392f92781fe8de1ed959f9e4bec348944e73e0"
    "ffd6889f46a911e72408e760f1ed5dae5c365d14fe8117af736a7f004d08c5c0c8e1d96ac9b59d85"
    "4374bebcff74cf7f204b988635a24ddb230afdb3ee49cb372748194ca4c255157e45889f546a19de"
    "49ec9b2969e1ddb48cace7e72c"
)
_ECDSA_HASH_DO_BU = bytes.fromhex(
    "f0b996f130402bf0a9790856a79219cf19aae3843810b0527b82236d920f408b29b44083e05ec14c"
    "c0ac777f2fe1f677e5b05ff6fc9e6f058ad39a011ee8f404"
)
_ECDSA_ASSINATURA = bytes.fromhex(
    "308188024200b186c2701e4ee0dd5cba3b2fb85084a03b57e7649fae750a9264117bda78a6e02c41"
    "d08fcc19921f1191b047298e05807f9dd12ba53aa52ee8809fd4581fd703e9024200945defdfd5d0"
    "b99c553f11b1eb1f87e4848529b62da1f6b152bb36d2efa9836aaba95bd9d1416671329d84082078"
    "fc6a767b34ba54d2e2c76892d6e35b834d30a2"
)


def _chave_ed(x: int, y: int) -> bytes:
    return curvas.codificar_ponto_ed521((x, y, 1, x * y % ((1 << 521) - 1)))


def _alterado(dados: bytes, posicao: int) -> bytes:
    return dados[:posicao] + bytes([dados[posicao] ^ 1]) + dados[posicao + 1 :]


def test_group_orders_send_the_generators_to_the_neutral_point() -> None:
    neutro = curvas.multiplicar_ed521(curvas.ORDEM_ED521, curvas.GERADOR_ED521)
    assert neutro[0] % ((1 << 521) - 1) == 0
    assert (neutro[1] - neutro[2]) % ((1 << 521) - 1) == 0
    assert curvas.no_infinito_p521(curvas.multiplicar_p521(curvas.ORDEM_P521, curvas.GERADOR_P521))


def test_ed521_public_key_derives_from_the_ecpy_private_key() -> None:
    resumo = bytearray(hashlib.shake_256(_ED_PRIVADA.to_bytes(66, "big")).digest(132)[:66])
    resumo[0] &= 0xFC
    resumo[65] = 0x80
    publica = curvas.multiplicar_ed521(int.from_bytes(resumo, "little"), curvas.GERADOR_ED521)
    assert curvas.codificar_ponto_ed521(publica) == _chave_ed(_ED_X, _ED_Y)


def test_ed521_accepts_the_ecpy_vectors() -> None:
    assert curvas.verificar_ed521(_chave_ed(_ED_X, _ED_Y), _ED_MENSAGEM, _ED_ASSINATURA)
    assert curvas.verificar_ed521(_chave_ed(_X509_X, _X509_Y), _X509_TBS, _X509_ASSINATURA)


def test_ed521_rejects_any_changed_byte() -> None:
    chave = _chave_ed(_ED_X, _ED_Y)
    assert not curvas.verificar_ed521(chave, _ED_MENSAGEM + b".", _ED_ASSINATURA)
    for posicao in (0, 65, 66, 131):
        assert not curvas.verificar_ed521(chave, _ED_MENSAGEM, _alterado(_ED_ASSINATURA, posicao))
    assert not curvas.verificar_ed521(_alterado(chave, 3), _ED_MENSAGEM, _ED_ASSINATURA)
    assert not curvas.verificar_ed521(chave, _ED_MENSAGEM, _ED_ASSINATURA[:-1])


def test_ed521_rejects_scalar_out_of_range_and_points_off_the_curve() -> None:
    chave = _chave_ed(_ED_X, _ED_Y)
    s_grande = (int.from_bytes(_ED_ASSINATURA[66:], "little") + curvas.ORDEM_ED521).to_bytes(
        66, "little"
    )
    assert not curvas.verificar_ed521(chave, _ED_MENSAGEM, _ED_ASSINATURA[:66] + s_grande)
    assert curvas.decodificar_ponto_ed521(b"\xff" * 66) is None
    assert curvas.decodificar_ponto_ed521(b"\x00" * 65) is None
    assert curvas.decodificar_ponto_ed521((2).to_bytes(66, "little")) is None


def test_ecdsa_accepts_a_real_urn_signature_and_rejects_changes() -> None:
    resumo = hashlib.sha512(_ECDSA_HASH_DO_BU).digest()
    assert curvas.verificar_ecdsa_p521(_ECDSA_CHAVE, resumo, _ECDSA_ASSINATURA)
    assert not curvas.verificar_ecdsa_p521(_ECDSA_CHAVE, _alterado(resumo, 5), _ECDSA_ASSINATURA)
    assert not curvas.verificar_ecdsa_p521(_ECDSA_CHAVE, resumo, _alterado(_ECDSA_ASSINATURA, 20))
    assert not curvas.verificar_ecdsa_p521(_alterado(_ECDSA_CHAVE, 40), resumo, _ECDSA_ASSINATURA)


def test_ecdsa_accepts_a_signature_made_here_with_a_known_key() -> None:
    privada, efemera = 123456789, 987654321
    publica = curvas.multiplicar_p521(privada, curvas.GERADOR_P521)
    x, y = _afim(publica)
    resumo = hashlib.sha512(b"boletim").digest()
    r = _afim(curvas.multiplicar_p521(efemera, curvas.GERADOR_P521))[0] % curvas.ORDEM_P521
    e = int.from_bytes(resumo, "big")
    s = pow(efemera, -1, curvas.ORDEM_P521) * (e + r * privada) % curvas.ORDEM_P521
    chave = b"\x04" + x.to_bytes(66, "big") + y.to_bytes(66, "big")
    assert curvas.verificar_ecdsa_p521(chave, resumo, _der(r, s))
    assert not curvas.verificar_ecdsa_p521(chave, resumo, _der(r, curvas.ORDEM_P521 - s + 1))


def test_ecdsa_rejects_malformed_signatures_and_keys() -> None:
    resumo = hashlib.sha512(_ECDSA_HASH_DO_BU).digest()
    for ruim in (b"", b"\x31\x00", _ECDSA_ASSINATURA + b"\x00", _ECDSA_ASSINATURA[:-3], _der(0, 1)):
        assert not curvas.verificar_ecdsa_p521(_ECDSA_CHAVE, resumo, ruim)
    assert not curvas.verificar_ecdsa_p521(b"\x02" + _ECDSA_CHAVE[1:67], resumo, _ECDSA_ASSINATURA)


def test_dispatch_picks_the_algorithm_and_refuses_unknown_ones() -> None:
    resumo = hashlib.sha512(_ECDSA_HASH_DO_BU).digest()
    assert curvas.verificar_assinatura(ECDSA_P521, _ECDSA_CHAVE, resumo, _ECDSA_ASSINATURA)
    assert curvas.verificar_assinatura(ED521, _chave_ed(_ED_X, _ED_Y), _ED_MENSAGEM, _ED_ASSINATURA)
    assert not curvas.verificar_assinatura("cepesc", b"", b"", b"")


def _afim(ponto: tuple[int, int, int]) -> tuple[int, int]:
    p = (1 << 521) - 1
    z = pow(ponto[2], -1, p)
    return ponto[0] * z * z % p, ponto[1] * z * z * z % p


def _der(r: int, s: int) -> bytes:
    def inteiro(valor: int) -> bytes:
        corpo = valor.to_bytes(valor.bit_length() // 8 + 1, "big")
        return b"\x02" + bytes([len(corpo)]) + corpo

    corpo = inteiro(r) + inteiro(s)
    return b"\x30\x81" + bytes([len(corpo)]) + corpo
