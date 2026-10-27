"""HTML de "Como votou cada estado": barras de fatia e de diferença por UF.

A página é autossuficiente: CSS embutido, logomarcas em data URI e nenhum
script. Segue o tema do sistema (prefers-color-scheme); `data-tema` no <html>
força o claro ou o escuro.
"""

from collections.abc import Mapping
from datetime import datetime
from fractions import Fraction
from html import escape
from typing import Final

from eleicoes.domain.mapa import Marca, MarkMissingError
from eleicoes.domain.percentual import format_integer, format_percent, round_half_up
from eleicoes.domain.votos_por_estado import (
    EXTERIOR,
    LinhaEstado,
    VotosPorEstado,
    votos_compactos,
)

TITULO: Final = "Como votou cada estado"
_PERMILLE: Final = 1000
_ESTREITO: Final = Fraction(7, 100)
_ESCURA: Final = "#111111"
_BRANCA: Final = "#ffffff"
_CLARO: Final = """
  --fundo: #ffffff; --painel: #f6f6f4; --linha: #dedcd6; --texto: #1d1d1b;
  --mudo: #5f5e59; --eixo: #8a8882; --outros: #d4d2cc;
"""
_ESCURO: Final = """
  --fundo: #121212; --painel: #1c1c1c; --linha: #343434; --texto: #f1f0ec;
  --mudo: #aaa8a1; --eixo: #77756f; --outros: #4a4a48;
"""
_ESTILO: Final = (
    ":root {"
    + _CLARO
    + "color-scheme: light; }"
    + "@media (prefers-color-scheme: dark) { :root:not([data-tema='light']) {"
    + _ESCURO
    + "color-scheme: dark; } }"
    + ":root[data-tema='dark'] {"
    + _ESCURO
    + "color-scheme: dark; }"
    + """
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--fundo); color: var(--texto);
  font-family: "Segoe UI", "Noto Sans", "Liberation Sans", "DejaVu Sans", sans-serif;
  font-size: 15px; line-height: 1.4; font-variant-numeric: tabular-nums;
}
main { max-width: 1080px; margin: 0 auto; padding: 1.25rem 16px 2rem; }
h1 { font-size: clamp(1.5rem, 4vw, 2.1rem); margin: 0 0 .25rem; letter-spacing: -0.02em; }
.subtitulo { margin: 0 0 1rem; color: var(--mudo); }
.finalistas { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem; margin-bottom: 1rem; }
.finalista {
  display: flex; align-items: center; gap: .6rem; padding: .6rem .75rem;
  background: var(--painel); border-radius: .5rem; border-top: 4px solid var(--cor);
}
.finalista.b { flex-direction: row-reverse; text-align: right; }
.finalista img { width: 44px; height: 44px; object-fit: contain; flex: none; }
.finalista .partido { font-weight: 700; font-size: 1.05rem; }
.finalista .vitorias { color: var(--mudo); font-size: .9rem; }
.cabecalho, .estado {
  display: grid; grid-template-columns: minmax(8.5rem, 11rem) 1fr 1fr;
  gap: .25rem 1rem; align-items: center;
}
.cabecalho { color: var(--mudo); font-size: .8rem; padding: 0 0 .35rem;
  border-bottom: 1px solid var(--linha); }
.cabecalho .meio { text-align: center; }
.estado { padding: .45rem 0; border-bottom: 1px solid var(--linha); }
.nome { font-weight: 600; }
.nome .absolutos { display: block; font-weight: 400; color: var(--mudo); font-size: .78rem; }
.parcial {
  display: inline-block; margin-left: .3rem; padding: 0 .35rem; border-radius: .25rem;
  font-size: .72rem; font-weight: 600; background: var(--painel); color: var(--mudo);
  border: 1px solid var(--linha);
}
.fatias { display: flex; height: 1.6rem; border-radius: .25rem; overflow: hidden; }
.fatias span {
  display: flex; align-items: center; justify-content: center; min-width: 0;
  font-size: .8rem; font-weight: 700; white-space: nowrap; overflow: hidden;
}
.fatias .outros { background: var(--outros); }
.fatias .estreito { font-size: 0; }
.diferenca { display: grid; grid-template-columns: 1fr 1fr; height: 1.6rem; }
.diferenca .lado { display: flex; align-items: center; gap: .3rem; min-width: 0; }
.diferenca .lado-a { justify-content: flex-end; border-right: 1px solid var(--eixo); }
.diferenca .lado-b { justify-content: flex-start; }
.diferenca .barra {
  height: 1.1rem; flex: 0 0 calc((100% - 4.6rem) * var(--w)); border-radius: 2px;
}
.diferenca .rotulo { font-size: .8rem; font-weight: 700; white-space: nowrap; }
.secao { margin: 1.25rem 0 .25rem; font-size: .85rem; color: var(--mudo);
  text-transform: uppercase; letter-spacing: .04em; }
footer { margin-top: 1.25rem; color: var(--mudo); font-size: .88rem; }
footer p { margin: .3rem 0; }
footer .brasil { color: var(--texto); font-weight: 600; font-size: 1rem; }
@media (max-width: 640px) {
  .cabecalho { grid-template-columns: 1fr; }
  .cabecalho .lugar { display: none; }
  .estado { grid-template-columns: 1fr; }
  .finalista img { width: 34px; height: 34px; }
}
"""
)


def html_dos_estados(
    votos: VotosPorEstado,
    marcas: Mapping[int, Marca],
    gerado_em: datetime,
    dados_em: datetime,
) -> str:
    faltam = tuple(numero for numero in (votos.a, votos.b) if numero not in marcas)
    if faltam:
        raise MarkMissingError(faltam)
    marca_a, marca_b = marcas[votos.a], marcas[votos.b]
    maior = max((linha.diferenca for linha in _linhas(votos)), default=0)
    corpo = (
        _finalistas(votos, marca_a, marca_b)
        + _cabecalho(votos, marca_a, marca_b)
        + "".join(_estado(votos, linha, marca_a, marca_b, maior) for linha in votos.estados)
        + _exterior(votos, marca_a, marca_b, maior)
    )
    return (
        "<!DOCTYPE html>"
        '<html lang="pt-BR">'
        "<head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(TITULO)} · {votos.turno}º turno {votos.ano}</title>"
        f"<style>{_ESTILO}</style>"
        "</head><body><main>"
        f"<h1>{escape(TITULO)}</h1>"
        f'<p class="subtitulo">{escape(subtitulo(votos))}</p>'
        f"{corpo}"
        f"{_rodape(votos, marca_a, marca_b, gerado_em, dados_em)}"
        "</main></body></html>"
    )


def subtitulo(votos: VotosPorEstado) -> str:
    base = f"Presidente, {votos.turno}º turno de {votos.ano}. Em % dos votos válidos e na"
    fatia = votos.cobertura.total.fatia
    if fatia is None:
        baixadas = format_integer(votos.cobertura.total.com_boletim)
        return (
            f"{base} diferença de votos, com {baixadas} urnas com boletim baixado"
            " (o índice de download não informa quantas são esperadas)"
        )
    return f"{base} diferença de votos, com {_cobertura(fatia)} das urnas"


def _linhas(votos: VotosPorEstado) -> tuple[LinhaEstado, ...]:
    if votos.exterior is None:
        return votos.estados
    return (*votos.estados, votos.exterior)


def _finalistas(votos: VotosPorEstado, marca_a: Marca, marca_b: Marca) -> str:
    return (
        '<div class="finalistas">'
        + _finalista("a", votos.a, marca_a, votos.vitorias_a)
        + _finalista("b", votos.b, marca_b, votos.vitorias_b)
        + "</div>"
    )


def _finalista(lado: str, numero: int, marca: Marca, vitorias: int) -> str:
    estados = "estado" if vitorias == 1 else "estados"
    return (
        f'<div class="finalista {lado}" style="--cor: {escape(marca.cor)}">'
        f'<img src="{escape(marca.logo)}" alt="Logomarca do {escape(_sigla(numero, marca))}">'
        "<div>"
        f'<div class="partido">{escape(_sigla(numero, marca))} · {numero}</div>'
        f'<div class="vitorias">venceu em {vitorias} {estados}</div>'
        "</div></div>"
    )


def _cabecalho(votos: VotosPorEstado, marca_a: Marca, marca_b: Marca) -> str:
    fatia = "% dos votos válidos" + (
        " (demais candidatos omitidos)" if votos.demais_omitidos else ""
    )
    return (
        '<div class="cabecalho" aria-hidden="true">'
        '<span class="lugar">Estado</span>'
        f'<span class="meio">{escape(fatia)}</span>'
        f'<span class="meio">← {escape(_sigla(votos.a, marca_a))} · Diferença de votos ·'
        f" {escape(_sigla(votos.b, marca_b))} →</span>"
        "</div>"
    )


def _estado(
    votos: VotosPorEstado, linha: LinhaEstado, marca_a: Marca, marca_b: Marca, maior: int
) -> str:
    parcial = votos.parcial(linha.uf)
    selo = (
        ""
        if parcial is None
        else f'<span class="parcial">parcial: {_cobertura(parcial)} das urnas</span>'
    )
    absolutos = (
        f"{votos.a}: {format_integer(linha.votos_a)} · {votos.b}: {format_integer(linha.votos_b)}"
    )
    return (
        f'<div class="estado" data-uf="{escape(linha.uf)}" title="{escape(_dica(votos, linha))}">'
        f'<div class="nome">{escape(linha.nome)}{selo}'
        f'<span class="absolutos">{escape(absolutos)}</span></div>'
        f"{_fatias(votos, linha, marca_a, marca_b)}"
        f"{_diferenca(votos, linha, marca_a, marca_b, maior)}"
        "</div>"
    )


def _dica(votos: VotosPorEstado, linha: LinhaEstado) -> str:
    return (
        f"{linha.nome}: {votos.a} {format_integer(linha.votos_a)} votos"
        f" ({format_percent(linha.fatia_a)}), {votos.b} {format_integer(linha.votos_b)} votos"
        f" ({format_percent(linha.fatia_b)}), diferença de {format_integer(linha.diferenca)}"
        f" em {format_integer(linha.validos)} válidos"
    )


def _fatias(votos: VotosPorEstado, linha: LinhaEstado, marca_a: Marca, marca_b: Marca) -> str:
    outros = 1 - linha.fatia_a - linha.fatia_b
    rotulo = f"{votos.a} {_um_decimal(linha.fatia_a)}, {votos.b} {_um_decimal(linha.fatia_b)}" + (
        f", demais {_um_decimal(outros)}" if outros > 0 else ""
    )
    return (
        f'<div class="fatias" role="img" aria-label="{escape(rotulo)}">'
        + _segmento(linha.fatia_a, marca_a.cor)
        + (f'<span class="outros" style="flex: {_flex(outros)}"></span>' if outros > 0 else "")
        + _segmento(linha.fatia_b, marca_b.cor)
        + "</div>"
    )


def _segmento(fatia: Fraction, cor: str) -> str:
    if fatia <= 0:
        return ""
    classe = ' class="estreito"' if fatia < _ESTREITO else ""
    return (
        f'<span{classe} style="flex: {_flex(fatia)}; background: {escape(cor)};'
        f' color: {_texto_sobre(cor)}">{_um_decimal(fatia)}</span>'
    )


def _diferenca(
    votos: VotosPorEstado, linha: LinhaEstado, marca_a: Marca, marca_b: Marca, maior: int
) -> str:
    vencedor = linha.vencedor(votos.a, votos.b)
    largura = _flex(Fraction(linha.diferenca, maior)) if maior else "0"
    rotulo = f"+{votos_compactos(linha.diferenca)}"
    lado_a = lado_b = ""
    if vencedor == votos.a:
        lado_a = _barra(rotulo, marca_a.cor, largura, antes=True)
    elif vencedor == votos.b:
        lado_b = _barra(rotulo, marca_b.cor, largura, antes=False)
    descricao = (
        "empate"
        if vencedor is None
        else f"{vencedor} à frente por {format_integer(linha.diferenca)} votos"
    )
    return (
        f'<div class="diferenca" role="img" aria-label="{escape(descricao)}">'
        f'<div class="lado lado-a">{lado_a}</div>'
        f'<div class="lado lado-b">{lado_b}</div>'
        "</div>"
    )


def _barra(rotulo: str, cor: str, largura: str, *, antes: bool) -> str:
    texto = f'<span class="rotulo" style="color: {escape(cor)}">{escape(rotulo)}</span>'
    barra = f'<span class="barra" style="--w: {largura}; background: {escape(cor)}"></span>'
    return texto + barra if antes else barra + texto


def _exterior(votos: VotosPorEstado, marca_a: Marca, marca_b: Marca, maior: int) -> str:
    if votos.exterior is None:
        return ""
    return '<p class="secao">Exterior</p>' + _estado(votos, votos.exterior, marca_a, marca_b, maior)


def _rodape(
    votos: VotosPorEstado,
    marca_a: Marca,
    marca_b: Marca,
    gerado_em: datetime,
    dados_em: datetime,
) -> str:
    brasil = votos.brasil
    total = (
        f"Brasil: {votos.a} {format_percent(brasil.fatia_a)} × {votos.b}"
        f" {format_percent(brasil.fatia_b)}, diferença de {format_integer(brasil.diferenca)}"
        " votos"
    )
    if votos.faltando or votos.exterior is None:
        total += " (só os lugares já importados)"
    linhas = [f'<p class="brasil">{escape(total)}</p>']
    linhas.append(
        _p(
            f"{_sigla(votos.a, marca_a)} ({votos.a}): {format_integer(brasil.votos_a)} votos."
            f" {_sigla(votos.b, marca_b)} ({votos.b}): {format_integer(brasil.votos_b)} votos."
            f" Válidos: {format_integer(brasil.validos)}."
        )
    )
    if votos.demais_omitidos:
        linhas.append(
            _p(
                "Os demais candidatos ficam fora das barras. As fatias são sobre todos os votos"
                " válidos; a parte cinza é a soma dos outros."
            )
        )
    if votos.faltando:
        linhas.append(_p(f"Ainda sem {votos.turno}º turno: {', '.join(votos.faltando)}."))
    if votos.exterior is None:
        linhas.append(_p(f"O Exterior ({EXTERIOR}) ainda não tem {votos.turno}º turno importado."))
    linhas.append(_p(_nota_cobertura(votos)))
    linhas.append(
        _p(
            "Fonte: boletins de urna do TSE importados no banco. Votos gravados em"
            f" {_momento(dados_em)}; página gerada em {_momento(gerado_em)}."
        )
    )
    return "<footer>" + "".join(linhas) + "</footer>"


def _nota_cobertura(votos: VotosPorEstado) -> str:
    total = votos.cobertura.total
    baixadas = format_integer(total.com_boletim)
    if total.esperadas is None:
        return (
            f"Urnas: {baixadas} seções com boletim baixado. O índice de download só lista as"
            " seções que o TSE já publicou, então não dá o total esperado."
        )
    base = (
        "seções do 1º turno no índice de download, as mesmas que votam no 2º"
        if votos.turno != votos.cobertura.base
        else f"seções do {votos.turno}º turno no índice de download"
    )
    return (
        f"Urnas: {baixadas} de {format_integer(total.esperadas)} seções com boletim baixado"
        f" (base: {base}). A imagem do boletim que falta não conta como urna faltando."
        " Boletim baixado ainda pode não estar importado: os votos só somam as UFs do banco."
    )


def _p(texto: str) -> str:
    return f"<p>{escape(texto)}</p>"


def _sigla(numero: int, marca: Marca) -> str:
    return marca.sigla or str(numero)


def _cobertura(fatia: Fraction) -> str:
    """Duas casas, truncadas: com uma urna faltando, nunca arredonda para 100%."""
    if fatia >= 1:
        return "100%"
    centesimos = int(fatia * 10_000)
    inteiro, resto = divmod(centesimos, 100)
    return f"{format_integer(inteiro)},{resto:02d}%"


def _um_decimal(fatia: Fraction) -> str:
    milesimos = round_half_up(fatia * _PERMILLE)
    inteiro, resto = divmod(milesimos, 10)
    return f"{format_integer(inteiro)},{resto}%"


def _flex(fatia: Fraction) -> str:
    return f"{float(fatia):.5f}"


def _texto_sobre(cor: str) -> str:
    """A cor de texto, preta ou branca, de maior contraste WCAG sobre o fundo."""
    fundo = _luminancia(cor)
    contra_escura = (fundo + 0.05) / (_luminancia(_ESCURA) + 0.05)
    contra_branca = (_luminancia(_BRANCA) + 0.05) / (fundo + 0.05)
    return _ESCURA if contra_escura >= contra_branca else _BRANCA


def _luminancia(cor: str) -> float:
    canais = (int(cor[indice : indice + 2], 16) / 255 for indice in (1, 3, 5))
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canais)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _momento(quando: datetime) -> str:
    return quando.astimezone().strftime("%d/%m/%Y %H:%M")
