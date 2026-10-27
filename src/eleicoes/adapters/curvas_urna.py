"""Verificação das assinaturas da urna: Ed521 (UE2020 e UE2022) e ECDSA P-521 (modelos antigos).

Nenhuma das duas curvas tem suporte na biblioteca padrão, e o Ed521 não existe no OpenSSL nem
no pacote cryptography. A conta segue o script de verificação que o TSE publica com a
documentação técnica da urna (lib/mr_util.py, que usa o ECPy):

* Ed521: EdDSA sobre a curva de Edwards E-521 (x² + y² = 1 − 376014·x²·y², p = 2^521 − 1),
  hash SHAKE256 com 132 bytes e o prefixo "SigEd521\\0\\0", pontos e escalares em 66 bytes
  little-endian, assinatura R‖S;
* ECDSA: curva NIST P-521, assinatura DER (r, s) sobre um resumo SHA-512 já calculado.

Só verificação: aqui não há chave privada, e o tempo constante não importa. As tabelas de
base fixa (gerador e chaves das autoridades) são montadas uma vez por processo.
"""

import hashlib
from functools import lru_cache
from typing import Final

from eleicoes.domain.assinatura_urna import ECDSA_P521, ED521

# --- Ed521 -------------------------------------------------------------------------------------

_P: Final = (1 << 521) - 1
_D: Final = _P - 376014
_N_ED: Final = (
    1 << 519
) - 337554763258501705789107630418782636071904961214051226618635150085779108655765
_GX_ED: Final = int(
    "752cb45c48648b189df90cb2296b2878a3bfd9f42fc6c818ec8bf3c9c0c6203913f6ecc5ccc72434"
    "b1ae949d568fc99c6059d0fb13364838aa302a940a2f19ba6c",
    16,
)
_GY_ED: Final = 12
_TAMANHO_ED: Final = 66
_PREFIXO_ED: Final = b"SigEd521\x00\x00"
_BIT_SINAL: Final = 8 * _TAMANHO_ED - 1

PontoEd = tuple[int, int, int, int]  # coordenadas estendidas (X, Y, Z, T), x = X/Z, y = Y/Z
_NEUTRO_ED: Final[PontoEd] = (0, 1, 1, 0)


def _soma_ed(p: PontoEd, q: PontoEd) -> PontoEd:
    x1, y1, z1, t1 = p
    x2, y2, z2, t2 = q
    a = x1 * x2 % _P
    b = y1 * y2 % _P
    c = _D * t1 % _P * t2 % _P
    d = z1 * z2 % _P
    e = ((x1 + y1) * (x2 + y2) - a - b) % _P
    f = d - c
    g = d + c
    h = b - a
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _dobro_ed(p: PontoEd) -> PontoEd:
    x1, y1, z1, _ = p
    a = x1 * x1 % _P
    b = y1 * y1 % _P
    c = 2 * z1 * z1 % _P
    e = ((x1 + y1) * (x1 + y1) - a - b) % _P
    g = a + b
    f = g - c
    h = a - b
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _iguais_ed(p: PontoEd, q: PontoEd) -> bool:
    return (p[0] * q[2] - q[0] * p[2]) % _P == 0 and (p[1] * q[2] - q[1] * p[2]) % _P == 0


def decodificar_ponto_ed521(codificado: bytes) -> PontoEd | None:
    """y em little-endian; o bit mais alto do último byte é a paridade de x."""
    if len(codificado) != _TAMANHO_ED:
        return None
    valor = int.from_bytes(codificado, "little")
    sinal = valor >> _BIT_SINAL
    y = valor & ((1 << _BIT_SINAL) - 1)
    if y >= _P:
        return None
    yy = y * y % _P
    xx = (1 - yy) * pow(1 - _D * yy, -1, _P) % _P
    x = pow(xx, (_P + 1) // 4, _P)  # p ≡ 3 (mod 4)
    if x * x % _P != xx:
        return None
    if x & 1 != sinal:
        x = _P - x
    return (x, y, 1, x * y % _P)


def codificar_ponto_ed521(ponto: PontoEd) -> bytes:
    x, y, z, _ = ponto
    inverso = pow(z, -1, _P)
    x = x * inverso % _P
    y = y * inverso % _P
    return (y | ((x & 1) << _BIT_SINAL)).to_bytes(_TAMANHO_ED, "little")


def multiplicar_ed521(escalar: int, ponto: PontoEd) -> PontoEd:
    """Janela fixa de 4 bits."""
    tabela = [_NEUTRO_ED, ponto]
    for _ in range(14):
        tabela.append(_soma_ed(tabela[-1], ponto))
    acumulado = _NEUTRO_ED
    for deslocamento in range(((escalar.bit_length() + 3) // 4 - 1) * 4, -1, -4):
        for _ in range(4):
            acumulado = _dobro_ed(acumulado)
        janela = (escalar >> deslocamento) & 0xF
        if janela:
            acumulado = _soma_ed(acumulado, tabela[janela])
    return acumulado


GERADOR_ED521: Final[PontoEd] = (_GX_ED, _GY_ED, 1, _GX_ED * _GY_ED % _P)
ORDEM_ED521: Final = _N_ED


@lru_cache(maxsize=1)
def _tabela_gerador_ed() -> list[list[PontoEd]]:
    """tabela[i][j] = j·256^i·G: [k]G vira uma soma por byte de k."""
    linhas: list[list[PontoEd]] = []
    base = GERADOR_ED521
    for _ in range(_TAMANHO_ED):
        linha = [_NEUTRO_ED, base]
        for _ in range(254):
            linha.append(_soma_ed(linha[-1], base))
        linhas.append(linha)
        base = _soma_ed(linha[-1], base)
    return linhas


def _vezes_gerador_ed(escalar: int) -> PontoEd:
    acumulado = _NEUTRO_ED
    for linha, byte in zip(
        _tabela_gerador_ed(), escalar.to_bytes(_TAMANHO_ED, "little"), strict=True
    ):
        if byte:
            acumulado = _soma_ed(acumulado, linha[byte])
    return acumulado


def verificar_ed521(chave: bytes, mensagem: bytes, assinatura: bytes) -> bool:
    """[S]B = R + [k]A, com k = SHAKE256(prefixo ‖ R ‖ A ‖ mensagem) mod ordem."""
    if len(assinatura) != 2 * _TAMANHO_ED:
        return False
    ponto_a = decodificar_ponto_ed521(chave)
    codificado_r = assinatura[:_TAMANHO_ED]
    ponto_r = decodificar_ponto_ed521(codificado_r)
    s = int.from_bytes(assinatura[_TAMANHO_ED:], "little")
    if ponto_a is None or ponto_r is None or s >= _N_ED:
        return False
    resumo = hashlib.shake_256(_PREFIXO_ED + codificado_r + chave + mensagem).digest(132)
    k = int.from_bytes(resumo, "little") % _N_ED
    esquerda = _soma_ed(ponto_r, multiplicar_ed521(k, ponto_a))
    return _iguais_ed(esquerda, _vezes_gerador_ed(s))


# --- ECDSA P-521 -------------------------------------------------------------------------------

_B_P521: Final = int(
    "0051953eb9618e1c9a1f929a21a0b68540eea2da725b99b315f3b8b489918ef109e156193951ec7e937b"
    "1652c0bd3bb1bf073573df883d2c34f1ef451fd46b503f00",
    16,
)
_GX_P521: Final = int(
    "00c6858e06b70404e9cd9e3ecb662395b4429c648139053fb521f828af606b4d3dbaa14b5e77efe75928"
    "fe1dc127a2ffa8de3348b3c1856a429bf97e7e31c2e5bd66",
    16,
)
_GY_P521: Final = int(
    "011839296a789a3bc0045c8a5fb42c7d1bd998f54449579b446817afbd17273e662c97ee72995ef42640"
    "c550b9013fad0761353c7086a272c24088be94769fd16650",
    16,
)
ORDEM_P521: Final = int(
    "01ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    "fa51868783bf2f966b7fcc0148f709a5d03bb5c9b8899c47aebb6fb71e91386409",
    16,
)
_BYTES_P521: Final = 66

PontoJ = tuple[
    int, int, int
]  # coordenadas jacobianas (X, Y, Z), x = X/Z², y = Y/Z³; Z = 0 é o infinito
_INFINITO: Final[PontoJ] = (1, 1, 0)
GERADOR_P521: Final[PontoJ] = (_GX_P521, _GY_P521, 1)


def _dobro_j(p: PontoJ) -> PontoJ:
    x1, y1, z1 = p
    if z1 == 0 or y1 == 0:
        return _INFINITO
    zz = z1 * z1 % _P
    m = 3 * (x1 - zz) * (x1 + zz) % _P  # a = −3
    yy = y1 * y1 % _P
    s = 4 * x1 * yy % _P
    x3 = (m * m - 2 * s) % _P
    y3 = (m * (s - x3) - 8 * yy * yy) % _P
    z3 = 2 * y1 * z1 % _P
    return (x3, y3, z3)


def _soma_j(p: PontoJ, q: PontoJ) -> PontoJ:
    x1, y1, z1 = p
    x2, y2, z2 = q
    if z1 == 0:
        return q
    if z2 == 0:
        return p
    z1z1 = z1 * z1 % _P
    z2z2 = z2 * z2 % _P
    u1 = x1 * z2z2 % _P
    u2 = x2 * z1z1 % _P
    s1 = y1 * z2 % _P * z2z2 % _P
    s2 = y2 * z1 % _P * z1z1 % _P
    h = (u2 - u1) % _P
    r = (s2 - s1) % _P
    if h == 0:
        return _dobro_j(p) if r == 0 else _INFINITO
    hh = h * h % _P
    hhh = h * hh % _P
    v = u1 * hh % _P
    x3 = (r * r - hhh - 2 * v) % _P
    y3 = (r * (v - x3) - s1 * hhh) % _P
    z3 = z1 * z2 % _P * h % _P
    return (x3, y3, z3)


def multiplicar_p521(escalar: int, ponto: PontoJ) -> PontoJ:
    tabela = [_INFINITO, ponto]
    for _ in range(14):
        tabela.append(_soma_j(tabela[-1], ponto))
    acumulado = _INFINITO
    for deslocamento in range(((escalar.bit_length() + 3) // 4 - 1) * 4, -1, -4):
        for _ in range(4):
            acumulado = _dobro_j(acumulado)
        janela = (escalar >> deslocamento) & 0xF
        if janela:
            acumulado = _soma_j(acumulado, tabela[janela])
    return acumulado


@lru_cache(maxsize=1)
def _tabela_gerador_p521() -> list[list[PontoJ]]:
    linhas: list[list[PontoJ]] = []
    base = GERADOR_P521
    for _ in range(_BYTES_P521):
        linha = [_INFINITO, base]
        for _ in range(254):
            linha.append(_soma_j(linha[-1], base))
        linhas.append(linha)
        base = _soma_j(linha[-1], base)
    return linhas


def _vezes_gerador_p521(escalar: int) -> PontoJ:
    acumulado = _INFINITO
    for linha, byte in zip(
        _tabela_gerador_p521(), escalar.to_bytes(_BYTES_P521, "little"), strict=True
    ):
        if byte:
            acumulado = _soma_j(acumulado, linha[byte])
    return acumulado


def no_infinito_p521(ponto: PontoJ) -> bool:
    return ponto[2] % _P == 0


def decodificar_ponto_p521(codificado: bytes) -> PontoJ | None:
    """Só o formato não comprimido (04 ‖ X ‖ Y), o único que os certificados da urna usam."""
    if len(codificado) != 1 + 2 * _BYTES_P521 or codificado[0] != 4:
        return None
    x = int.from_bytes(codificado[1 : 1 + _BYTES_P521], "big")
    y = int.from_bytes(codificado[1 + _BYTES_P521 :], "big")
    if x >= _P or y >= _P or (y * y - x * x * x + 3 * x - _B_P521) % _P:
        return None
    return (x, y, 1)


def _assinatura_der(der: bytes) -> tuple[int, int] | None:
    """SEQUENCE { INTEGER r, INTEGER s }, comprimento curto ou de um byte."""
    try:
        if der[0] != 0x30:
            return None
        posicao, comprimento = _comprimento(der, 1)
        if posicao + comprimento != len(der):
            return None
        valores: list[int] = []
        for _ in range(2):
            if der[posicao] != 0x02:
                return None
            posicao, comprimento = _comprimento(der, posicao + 1)
            valores.append(int.from_bytes(der[posicao : posicao + comprimento], "big"))
            posicao += comprimento
    except IndexError:
        return None
    if posicao != len(der):
        return None
    return valores[0], valores[1]


def _comprimento(der: bytes, posicao: int) -> tuple[int, int]:
    primeiro = der[posicao]
    if primeiro < 0x80:
        return posicao + 1, primeiro
    bytes_comprimento = primeiro & 0x7F
    fim = posicao + 1 + bytes_comprimento
    return fim, int.from_bytes(der[posicao + 1 : fim], "big")


def verificar_ecdsa_p521(chave: bytes, resumo: bytes, assinatura: bytes) -> bool:
    """ECDSA sobre um resumo já calculado (o script do TSE passa SHA-512 do hash do arquivo)."""
    ponto_q = decodificar_ponto_p521(chave)
    rs = _assinatura_der(assinatura)
    if ponto_q is None or rs is None:
        return False
    r, s = rs
    if not (0 < r < ORDEM_P521 and 0 < s < ORDEM_P521):
        return False
    e = int.from_bytes(resumo, "big") >> max(0, 8 * len(resumo) - ORDEM_P521.bit_length())
    w = pow(s, -1, ORDEM_P521)
    soma = _soma_j(
        _vezes_gerador_p521(e * w % ORDEM_P521), multiplicar_p521(r * w % ORDEM_P521, ponto_q)
    )
    if no_infinito_p521(soma):
        return False
    x = soma[0] * pow(soma[2] * soma[2] % _P, -1, _P) % _P
    return x % ORDEM_P521 == r


def verificar_assinatura(algoritmo: str, chave: bytes, mensagem: bytes, assinatura: bytes) -> bool:
    """O Verificador do domínio: Ed521 recebe a mensagem; ECDSA, o resumo SHA-512."""
    if algoritmo == ED521:
        return verificar_ed521(chave, mensagem, assinatura)
    if algoritmo == ECDSA_P521:
        return verificar_ecdsa_p521(chave, mensagem, assinatura)
    return False
