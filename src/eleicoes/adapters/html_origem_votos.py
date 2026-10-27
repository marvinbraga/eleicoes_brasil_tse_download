"""HTML de "De onde vieram os votos": fontes dos votos novos dos finalistas, por município.

Página autocontida, sem CDN: CSS próprio com tema claro e escuro, gráficos em SVG.
"""

import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from fractions import Fraction
from html import escape
from typing import Final

from eleicoes.domain.origem_votos import (
    MINIMO_DE_FINALISTAS,
    REGIAO_EXTERIOR,
    Balanco,
    Dispersao,
    LugarAusente,
    MunicipioOrigem,
    OrigemDosVotos,
    Ponto,
)
from eleicoes.domain.percentual import format_integer, format_percent
from eleicoes.domain.regiao import REGIONS

TITULO: Final = "De onde vieram os votos"
COR_PADRAO: Final = "#8a8f98"
LIMITE_DE_FALHAS: Final = 300
_HEX: Final = re.compile(r"#[0-9a-fA-F]{6}")
LIMITE_DE_AUSENTES: Final = 60
_LARGURA: Final = 640
_ALTURA: Final = 420
_MARGEM_ESQ: Final = 56
_MARGEM_DIR: Final = 16
_MARGEM_TOPO: Final = 16
_MARGEM_BASE: Final = 44
_CORTE: Final = 0.005
_Escala = Callable[[float], float]
_REGIOES: Final[tuple[str, ...]] = (*(regiao.name for regiao in REGIONS), REGIAO_EXTERIOR)
_CLASSE_REGIAO: Final[dict[str, str]] = {
    nome: f"r{indice}" for indice, nome in enumerate(_REGIOES, start=1)
}
_ESTILO: Final = """
:root {
  color-scheme: light;
  --fundo: #f7f7f5; --painel: #ffffff; --linha: #dcdcd6; --grade: #ecece6;
  --texto: #161616; --mudo: #55554f; --destaque: #0d6f6e; --alerta: #9a3412;
  --r1: #1baf7a; --r2: #eb6834; --r3: #c98500; --r4: #6250d6; --r5: #d55181; --r6: #8a8f98;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --fundo: #101616; --painel: #182220; --linha: #314340; --grade: #23302e;
    --texto: #e7f1ed; --mudo: #a8c2bc; --destaque: #5cc8c6; --alerta: #fdba74;
    --r1: #199e70; --r2: #d95926; --r3: #eda100; --r4: #9085e9; --r5: #e87ba4; --r6: #9aa0a8;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --fundo: #101616; --painel: #182220; --linha: #314340; --grade: #23302e;
  --texto: #e7f1ed; --mudo: #a8c2bc; --destaque: #5cc8c6; --alerta: #fdba74;
  --r1: #199e70; --r2: #d95926; --r3: #eda100; --r4: #9085e9; --r5: #e87ba4; --r6: #9aa0a8;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--fundo); color: var(--texto);
  font-family: "Segoe UI", "Noto Sans", "Liberation Sans", "DejaVu Sans", sans-serif;
  font-size: 15px; line-height: 1.45;
}
main { max-width: 1440px; margin-inline: auto; padding: 1.5rem 16px; }
h1 {
  font-family: Palatino, "Palatino Linotype", "Liberation Serif", Georgia, serif;
  font-size: clamp(1.7rem, 3vw, 2.4rem); font-weight: 600; margin: 0 0 .25rem;
}
h2 { font-size: 1.3rem; margin: 2.2rem 0 .6rem; }
h3 { font-size: 1.05rem; margin: 1.2rem 0 .4rem; }
p, li { max-width: 80ch; }
.subtitulo, .mudo { color: var(--mudo); }
.aviso { border-left: 3px solid var(--alerta); padding: .4rem .8rem; background: var(--painel); }
.cartoes { display: grid; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); gap: .8rem; }
.cartao { background: var(--painel); border: 1px solid var(--linha); border-radius: 8px;
  padding: .8rem 1rem; }
.cartao .rotulo { color: var(--mudo); font-size: .85rem; }
.cartao .valor { font-size: 1.5rem; font-variant-numeric: tabular-nums; font-weight: 600; }
.cartao .detalhe { color: var(--mudo); font-size: .85rem; font-variant-numeric: tabular-nums; }
.marca { display: inline-block; width: .8em; height: .8em; border-radius: 2px; margin-right: .3em;
  vertical-align: baseline; }
.barra { display: flex; height: 14px; border-radius: 4px; overflow: hidden; gap: 2px;
  margin: .4rem 0; }
.barra span { display: block; height: 100%; }
.identidade { font-family: ui-monospace, "DejaVu Sans Mono", monospace; background: var(--painel);
  border: 1px solid var(--linha); border-radius: 6px; padding: .6rem .8rem; overflow-x: auto;
  white-space: nowrap; }
.rolagem { overflow: auto; max-height: 70vh; border: 1px solid var(--linha); border-radius: 6px; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums;
  font-size: .88rem; }
th, td { padding: .3rem .5rem; border-bottom: 1px solid var(--linha); white-space: nowrap; }
td.num, th.num { text-align: right; }
th.lugar, td.lugar { text-align: left; position: sticky; left: 0; background: var(--painel);
  z-index: 1; }
thead th { position: sticky; top: 0; background: var(--painel); z-index: 2; cursor: pointer;
  user-select: none; vertical-align: bottom; white-space: normal; min-width: 5.5rem; }
thead th.lugar { z-index: 3; }
thead th[aria-sort="ascending"]::after { content: " ▲"; }
thead th[aria-sort="descending"]::after { content: " ▼"; }
tbody tr:nth-child(even) td { background: color-mix(in srgb, var(--painel) 92%, var(--texto)); }
tfoot td { font-weight: 600; border-top: 2px solid var(--linha); }
td.falha { color: var(--alerta); font-weight: 600; }
.graficos { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 36rem), 1fr));
  gap: 1rem; }
figure { margin: 0; background: var(--painel); border: 1px solid var(--linha); border-radius: 8px;
  padding: .8rem; }
figcaption { font-weight: 600; margin-bottom: .3rem; }
svg.dispersao { width: 100%; height: auto; display: block; }
svg .eixo { stroke: var(--linha); stroke-width: 1; }
svg .grade { stroke: var(--grade); stroke-width: 1; }
svg .zero { stroke: var(--mudo); stroke-width: 1; stroke-dasharray: 3 3; }
svg .reta { stroke: var(--texto); stroke-width: 2; }
svg text { fill: var(--mudo); font-size: 11px; }
svg circle { fill-opacity: .55; stroke: var(--painel); stroke-width: .6; }
svg circle:hover { fill-opacity: 1; stroke: var(--texto); }
.r1 { fill: var(--r1); background: var(--r1); } .r2 { fill: var(--r2); background: var(--r2); }
.r3 { fill: var(--r3); background: var(--r3); } .r4 { fill: var(--r4); background: var(--r4); }
.r5 { fill: var(--r5); background: var(--r5); } .r6 { fill: var(--r6); background: var(--r6); }
.legenda { display: flex; flex-wrap: wrap; gap: .3rem 1rem; margin: .4rem 0; font-size: .85rem; }
.legenda label { cursor: pointer; }
.estatisticas { display: flex; flex-wrap: wrap; gap: .3rem 1.2rem; font-size: .88rem;
  margin-top: .4rem; }
.oculto { display: none; }
.notas { margin: 2rem 0 0; padding: 1rem 0 0 1.2rem; border-top: 1px solid var(--linha);
  color: var(--mudo); }
"""
_SCRIPT: Final = """
<script>
(function () {
  document.querySelectorAll("table.ordenavel").forEach(function (table) {
    table.querySelectorAll("thead th").forEach(function (header, index) {
      header.tabIndex = 0;
      header.addEventListener("click", function () { reorder(table, header, index); });
      header.addEventListener("keydown", function (event) {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        reorder(table, header, index);
      });
    });
  });

  function reorder(table, header, index) {
    var ascending = header.getAttribute("aria-sort") !== "ascending";
    table.querySelectorAll("thead th").forEach(function (item) {
      item.setAttribute("aria-sort", "none");
    });
    header.setAttribute("aria-sort", ascending ? "ascending" : "descending");
    var body = table.tBodies[0];
    var rows = Array.prototype.slice.call(body.rows);
    var sign = ascending ? 1 : -1;
    rows.sort(function (left, right) {
      var a = left.cells[index].getAttribute("data-ord") || "";
      var b = right.cells[index].getAttribute("data-ord") || "";
      if (index === 0) {
        return sign * a.localeCompare(b, "pt-BR", {numeric: true, sensitivity: "base"});
      }
      return sign * (Number(a) - Number(b));
    });
    rows.forEach(function (row) { body.appendChild(row); });
  }

  document.querySelectorAll("input[data-regiao]").forEach(function (caixa) {
    caixa.addEventListener("change", function () {
      var classe = caixa.getAttribute("data-regiao");
      document.querySelectorAll("svg.dispersao circle." + classe).forEach(function (ponto) {
        ponto.classList.toggle("oculto", !caixa.checked);
      });
      document.querySelectorAll("input[data-regiao='" + classe + "']").forEach(function (outra) {
        outra.checked = caixa.checked;
      });
    });
  });
})();
</script>
"""


@dataclass(frozen=True, slots=True)
class PaginaDaOrigem:
    """O que a página precisa além da análise: cores, siglas e as datas dos dados."""

    ano: int
    gerado_em: datetime
    origem: OrigemDosVotos
    cores: Mapping[int, str] = field(default_factory=dict)
    siglas: Mapping[int, str] = field(default_factory=dict)
    lugares_primeiro_em: datetime | None = None
    lugares_segundo_em: datetime | None = None
    carga_segundo_em: datetime | None = None


def html_da_origem(pagina: PaginaDaOrigem) -> str:
    origem = pagina.origem
    corpo = (
        _abertura(pagina)
        + "<h2>1. Totais das UFs comparadas</h2>"
        + _totais(pagina)
        + "<h3>Por UF</h3>"
        + _tabela_ufs(pagina)
        + "<h2>2. Virada × fontes, um ponto por município</h2>"
        + _graficos(pagina)
        + f"<h2>3. Maiores viradas para o {origem.a}</h2>"
        + _explica_topo(origem)
        + _tabela_topo(pagina, origem.topo_a)
        + f"<h2>Maiores viradas para o {origem.b}</h2>"
        + _tabela_topo(pagina, origem.topo_b)
        + "<h2>4. Conferência da identidade</h2>"
        + _conferencia(pagina)
    )
    itens = "".join(f"<li>{escape(nota)}</li>" for nota in notas(origem))
    return (
        "<!DOCTYPE html>"
        '<html lang="pt-BR">'
        "<head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(TITULO)}</title>"
        f"<style>{_ESTILO}</style>"
        "</head><body><main>"
        f"<h1>{escape(TITULO)}</h1>"
        f'<p class="subtitulo">{escape(_subtitulo(pagina))}</p>'
        f"{corpo}"
        f'<h2>Método</h2><ul class="notas">{itens}</ul>'
        "</main>"
        f"{_SCRIPT}"
        "</body></html>"
    )


def notas(origem: OrigemDosVotos) -> tuple[str, ...]:
    a, b = origem.a, origem.b
    return (
        f"Em cada município, as cédulas de presidente de um turno são os votos do {a}, do "
        f"{b}, dos eliminados (O) e os brancos e nulos (BN). Subtraindo o 1º turno do 2º: "
        f"Δ{a} + Δ{b} = O₁ − O₂ − ΔBN + Δcédulas. No 2º turno não há eliminados (O₂ = 0) e "
        f"as cédulas deveriam ser o comparecimento (C), então Δ{a} + Δ{b} = O₁ − ΔBN + ΔC.",
        "As três fontes dos votos novos dos finalistas: os votos dos eliminados no 1º turno "
        "(O₁), os brancos e nulos que deixaram de existir no 2º (−ΔBN; positivo quando o 2º "
        "turno teve menos brancos e nulos) e o comparecimento a mais (ΔC; negativo quando "
        "menos gente votou). Uma fonte negativa tira votos dos finalistas.",
        "A identidade é contábil: vale por construção. O resíduo Δ"
        f"{a} + Δ{b} − (O₁ − ΔBN + ΔC) é igual a (cédulas₂ − C₂) − (cédulas₁ − C₁) − O₂, então "
        "só sai diferente de zero quando as cédulas gravadas não batem com o comparecimento do "
        "boletim num dos turnos ou quando há voto fora dos finalistas no 2º turno. Isso é "
        "problema de dado (por exemplo, uma UF ainda carregando depois de os lugares serem "
        "gravados), não de comportamento do eleitor.",
        "A identidade diz quanto entrou de cada fonte, não para quem foi cada voto. Saber "
        "que o eliminado X apoiou um finalista não diz quantos eleitores de X o seguiram.",
        f"Virada é a fatia do {a} entre os votos dos dois finalistas no 2º turno menos a mesma "
        "fatia no 1º turno, em pontos percentuais. Positiva: o "
        f"{a} cresceu mais que o {b}, em proporção.",
        "As correlações e a reta são ponderadas pelas cédulas do 1º turno de cada município. "
        "O Spearman é o Pearson ponderado das posições; a posição de um município é o peso "
        "acumulado até ele, então cidade grande ocupa faixa larga. Os gráficos escondem os "
        f"{format_percent(Fraction(_CORTE).limit_denominator(1000))} mais extremos de cada "
        "lado de cada eixo para dar escala; as estatísticas usam todos os pontos.",
        "Correlação ecológica descreve municípios, não pessoas. Um município onde o "
        f"comparecimento subiu e o {a} ganhou fatia não mostra que os eleitores novos votaram "
        f"no {a}: o mesmo padrão aparece com muitas combinações de comportamento individual.",
        "Só entra o município com os dois turnos gravados e o comparecimento dos dois turnos "
        "lido do boletim. Os totais somam apenas as UFs comparadas; UF sem 2º turno no banco "
        "fica fora e aparece na abertura.",
        "Nada aqui prova ou descarta fraude. O relatório mostra de onde os votos novos podem "
        "ter vindo e confere se os números fecham; a interpretação fica com o leitor.",
    )


def _subtitulo(pagina: PaginaDaOrigem) -> str:
    origem = pagina.origem
    ufs = ", ".join(uf.uf for uf in origem.ufs)
    momento = pagina.gerado_em.astimezone().strftime("%Y-%m-%d %H:%M")
    return (
        f"Presidente {pagina.ano} · finalistas {_nome(pagina, origem.a)} e "
        f"{_nome(pagina, origem.b)} · UFs comparadas: {ufs} · gerado em {momento}"
    )


def _abertura(pagina: PaginaDaOrigem) -> str:
    origem = pagina.origem
    partes = [
        f"<p>{format_integer(len(origem.municipios))} municípios com os dois turnos e o "
        "comparecimento dos dois.",
    ]
    if origem.ufs_sem_segundo_turno:
        partes.append(
            " Sem 2º turno gravado, fora da comparação: "
            f"{escape(', '.join(origem.ufs_sem_segundo_turno))}."
        )
    partes.append("</p>")
    partes.append(_datas(pagina))
    partes.append(
        '<p class="aviso">Este relatório mostra de onde os votos novos dos finalistas podem ter '
        "vindo e confere a conta município a município. Ele não prova nem descarta fraude.</p>"
    )
    return "".join(partes)


def _datas(pagina: PaginaDaOrigem) -> str:
    itens: list[str] = []
    if pagina.lugares_primeiro_em is not None:
        itens.append(f"lugares do 1º turno gravados em {_momento(pagina.lugares_primeiro_em)}")
    if pagina.lugares_segundo_em is not None:
        itens.append(f"lugares do 2º turno gravados em {_momento(pagina.lugares_segundo_em)}")
    if pagina.carga_segundo_em is not None:
        itens.append(f"última carga de boletins do 2º turno em {_momento(pagina.carga_segundo_em)}")
    if not itens:
        return ""
    texto = "Dados: " + "; ".join(itens) + "."
    atrasado = (
        pagina.lugares_segundo_em is not None
        and pagina.carga_segundo_em is not None
        and pagina.carga_segundo_em > pagina.lugares_segundo_em
    )
    if atrasado:
        texto += (
            " Boletins chegaram depois de os lugares do 2º turno serem gravados: o "
            "comparecimento é lido agora e as cédulas são as gravadas, então a identidade pode "
            "falhar nas UFs que receberam boletins nesse intervalo."
        )
    return f'<p class="mudo">{escape(texto)}</p>'


def _momento(valor: datetime) -> str:
    return valor.astimezone().strftime("%Y-%m-%d %H:%M")


def _totais(pagina: PaginaDaOrigem) -> str:
    origem = pagina.origem
    total = origem.total
    cedulas = total.primeiro.cedulas
    novos = total.novos
    fontes = (
        ("Votos dos eliminados (O₁)", total.eliminados, "r6"),
        ("Brancos e nulos que viraram válidos (−ΔBN)", total.brancos_nulos_liberados, "r3"),
        ("Comparecimento a mais (ΔC)", total.delta_comparecimento, "r1"),
    )
    cartoes = [
        _cartao(
            f"Votos novos dos finalistas (Δ{origem.a} + Δ{origem.b})",
            format_integer(novos),
            f"{_pct(novos, cedulas)} das cédulas do 1º turno",
        )
    ]
    for rotulo, valor, _ in fontes:
        cartoes.append(
            _cartao(
                rotulo,
                format_integer(valor),
                f"{_pct(valor, novos)} dos votos novos · {_pct(valor, cedulas)} das cédulas do "
                "1º turno",
            )
        )
    for numero, delta, antes in (
        (origem.a, total.delta_a, total.primeiro.a),
        (origem.b, total.delta_b, total.primeiro.b),
    ):
        cartoes.append(
            _cartao(
                f'<span class="marca" style="background:{_cor(pagina, numero)}"></span>'
                f"Δ{escape(_nome(pagina, numero))}",
                format_integer(delta),
                f"{_pct(delta, antes)} sobre os votos do 1º turno · {_pct(delta, novos)} dos "
                "votos novos",
                rotulo_html=True,
            )
        )
    cartoes.append(
        _cartao(
            "Eleitores aptos (Δ)",
            format_integer(total.delta_aptos),
            f"{_pct(total.delta_aptos, total.primeiro.aptos)} sobre os aptos do 1º turno",
        )
    )
    return (
        f'<div class="cartoes">{"".join(cartoes)}</div>'
        + _barras(pagina, total, fontes)
        + _identidade(origem.a, origem.b, total)
    )


def _barras(
    pagina: PaginaDaOrigem, total: Balanco, fontes: tuple[tuple[str, int, str], ...]
) -> str:
    origem = pagina.origem
    if all(valor >= 0 for _, valor, _ in fontes) and total.novos > 0:
        fatias = "".join(
            f'<span class="{classe}" style="width:{_largura(valor, total.novos)}%" '
            f'title="{escape(rotulo)}: {format_integer(valor)}"></span>'
            for rotulo, valor, classe in fontes
        )
        legenda = "".join(
            f'<span><span class="marca {classe}"></span>{escape(rotulo)}</span>'
            for rotulo, _, classe in fontes
        )
        fontes_html = (
            "<h3>As três fontes dos votos novos</h3>"
            f'<div class="barra" role="img" aria-label="Fontes dos votos novos">{fatias}</div>'
            f'<div class="legenda">{legenda}</div>'
        )
    else:
        fontes_html = ""
    if total.delta_a >= 0 and total.delta_b >= 0 and total.novos > 0:
        divisao = "".join(
            f'<span style="width:{_largura(delta, total.novos)}%;background:'
            f'{_cor(pagina, numero)}" title="{escape(_nome(pagina, numero))}: '
            f'{format_integer(delta)}"></span>'
            for numero, delta in ((origem.a, total.delta_a), (origem.b, total.delta_b))
        )
        legenda_divisao = "".join(
            f'<span><span class="marca" style="background:{_cor(pagina, numero)}"></span>'
            f"{escape(_nome(pagina, numero))}: {format_integer(delta)} "
            f"({_pct(delta, total.novos)})</span>"
            for numero, delta in ((origem.a, total.delta_a), (origem.b, total.delta_b))
        )
        fontes_html += (
            "<h3>Quem levou os votos novos</h3>"
            f'<div class="barra" role="img" aria-label="Divisão dos votos novos">{divisao}</div>'
            f'<div class="legenda">{legenda_divisao}</div>'
        )
    return fontes_html


def _identidade(a: int, b: int, balanco: Balanco) -> str:
    return (
        "<h3>A conta</h3>"
        '<p class="identidade">'
        f"Δ{a} + Δ{b} = O₁ − ΔBN + ΔC<br>"
        f"{format_integer(balanco.delta_a)} + {format_integer(balanco.delta_b)} = "
        f"{format_integer(balanco.eliminados)} − ({format_integer(balanco.delta_branco_nulo)}) "
        f"+ {format_integer(balanco.delta_comparecimento)}<br>"
        f"{format_integer(balanco.novos)} = {format_integer(balanco.fontes)} · resíduo "
        f"{format_integer(balanco.residuo)}</p>"
    )


def _cartao(rotulo: str, valor: str, detalhe: str, *, rotulo_html: bool = False) -> str:
    texto = rotulo if rotulo_html else escape(rotulo)
    return (
        '<div class="cartao">'
        f'<div class="rotulo">{texto}</div>'
        f'<div class="valor">{escape(valor)}</div>'
        f'<div class="detalhe">{escape(detalhe)}</div>'
        "</div>"
    )


def _tabela_ufs(pagina: PaginaDaOrigem) -> str:
    origem = pagina.origem
    a, b = origem.a, origem.b
    cabecalho = (
        '<th class="lugar">UF</th>'
        + _th("Municípios")
        + _th("Cédulas 1º turno")
        + _th("O₁")
        + _th("O₁ % céd. 1º")
        + _th("−ΔBN")
        + _th("−ΔBN % céd. 1º")
        + _th("ΔC")
        + _th("ΔC % céd. 1º")
        + _th("Δ aptos")
        + _th(f"Δ{a} + Δ{b}")
        + _th(f"Δ{a}")
        + _th(f"Δ{a} % votos 1º")
        + _th(f"Δ{b}")
        + _th(f"Δ{b} % votos 1º")
        + _th(f"Parte do {a} nos novos")
        + _th(f"Parte do {b} nos novos")
        + _th("Virada (p.p.)")
        + _th("Municípios com resíduo")
    )
    linhas = "".join(_linha_uf(uf.uf, uf.municipios, uf.falhas, uf.balanco) for uf in origem.ufs)
    rodape = _linha_uf("Total", len(origem.municipios), len(origem.falhas), origem.total)
    return (
        '<div class="rolagem"><table class="ordenavel">'
        f"<thead><tr>{cabecalho}</tr></thead>"
        f"<tbody>{linhas}</tbody>"
        f"<tfoot>{rodape}</tfoot>"
        "</table></div>"
    )


def _linha_uf(rotulo: str, municipios: int, falhas: int, b: Balanco) -> str:
    cedulas = b.primeiro.cedulas
    classe_falha = " falha" if falhas else ""
    return (
        "<tr>"
        f'<td class="lugar" data-ord="{escape(rotulo)}">{escape(rotulo)}</td>'
        + _int(municipios)
        + _int(cedulas)
        + _int(b.eliminados)
        + _frac(b.eliminados, cedulas)
        + _int(b.brancos_nulos_liberados)
        + _frac(b.brancos_nulos_liberados, cedulas)
        + _int(b.delta_comparecimento)
        + _frac(b.delta_comparecimento, cedulas)
        + _int(b.delta_aptos)
        + _int(b.novos)
        + _int(b.delta_a)
        + _frac(b.delta_a, b.primeiro.a)
        + _int(b.delta_b)
        + _frac(b.delta_b, b.primeiro.b)
        + _frac(b.delta_a, b.novos)
        + _frac(b.delta_b, b.novos)
        + _pp(b.virada)
        + f'<td class="num{classe_falha}" data-ord="{falhas}">{format_integer(falhas)}</td>'
        + "</tr>"
    )


def _graficos(pagina: PaginaDaOrigem) -> str:
    origem = pagina.origem
    a = origem.a
    return (
        f"<p>Eixo vertical: virada da fatia do {escape(_nome(pagina, a))} entre os finalistas, "
        "em pontos percentuais (acima de zero, o "
        f"{a} ganhou fatia). Cada ponto é um município, com área proporcional às cédulas do "
        "1º turno; passe o mouse para ver qual. A linha é a reta ponderada. Clique na legenda "
        "para esconder uma região.</p>"
        '<div class="graficos">'
        + _figura(
            "Comparecimento a mais × virada",
            "ΔC em % das cédulas do 1º turno",
            origem.por_comparecimento,
            "comparecimento",
        )
        + _figura(
            "Peso dos eliminados × virada",
            "Eliminados em % dos votos válidos do 1º turno",
            origem.por_eliminados,
            "eliminados",
        )
        + "</div>"
    )


def _figura(titulo: str, eixo_x: str, dispersao: Dispersao, chave: str) -> str:
    return (
        "<figure>"
        f"<figcaption>{escape(titulo)}</figcaption>"
        + _legenda_regioes(dispersao.pontos, chave)
        + _svg(dispersao, eixo_x, titulo)
        + _estatisticas(dispersao)
        + "</figure>"
    )


def _legenda_regioes(pontos: Sequence[Ponto], chave: str) -> str:
    presentes = {ponto.regiao for ponto in pontos}
    itens = "".join(
        f'<label><input type="checkbox" checked data-regiao="{_CLASSE_REGIAO[nome]}" '
        f'name="{chave}-{_CLASSE_REGIAO[nome]}"> '
        f'<span class="marca {_CLASSE_REGIAO[nome]}"></span>{escape(nome)}</label>'
        for nome in _REGIOES
        if nome in presentes
    )
    return f'<div class="legenda">{itens}</div>'


def _estatisticas(dispersao: Dispersao) -> str:
    return (
        '<div class="estatisticas">'
        f"<span>Municípios: <strong>{format_integer(len(dispersao.pontos))}</strong></span>"
        f"<span>Pearson ponderado: <strong>{_correlacao(dispersao.pearson)}</strong></span>"
        f"<span>Spearman ponderado: <strong>{_correlacao(dispersao.spearman)}</strong></span>"
        f"<span>Inclinação: <strong>{_decimal(dispersao.inclinacao, 3)}</strong> p.p. por "
        "ponto do eixo x</span>"
        "</div>"
    )


def _svg(dispersao: Dispersao, eixo_x: str, titulo: str) -> str:
    pontos = dispersao.pontos
    if not pontos:
        return '<p class="mudo">Sem municípios para desenhar.</p>'
    x0, x1 = _faixa([ponto.x for ponto in pontos])
    y0, y1 = _faixa([ponto.y for ponto in pontos])
    largura = _LARGURA - _MARGEM_ESQ - _MARGEM_DIR
    altura = _ALTURA - _MARGEM_TOPO - _MARGEM_BASE

    def px(valor: float) -> float:
        return _MARGEM_ESQ + (valor - x0) / (x1 - x0) * largura

    def py(valor: float) -> float:
        return _MARGEM_TOPO + (y1 - valor) / (y1 - y0) * altura

    maior = max(ponto.peso for ponto in pontos)
    partes = [
        f'<svg class="dispersao" viewBox="0 0 {_LARGURA} {_ALTURA}" role="img" '
        f'aria-label="{escape(titulo)}">'
    ]
    partes.extend(_grade(x0, x1, px, horizontal=True))
    partes.extend(_grade(y0, y1, py, horizontal=False))
    if y0 < 0 < y1:
        partes.append(
            f'<line class="zero" x1="{_MARGEM_ESQ}" x2="{_MARGEM_ESQ + largura}" '
            f'y1="{py(0):.1f}" y2="{py(0):.1f}"/>'
        )
    ordenados = sorted(pontos, key=lambda ponto: -ponto.peso)
    for ponto in ordenados:
        if not (x0 <= ponto.x <= x1 and y0 <= ponto.y <= y1):
            continue
        raio = 1.5 + 9 * math.sqrt(ponto.peso / maior)
        dica = (
            f"{ponto.nome} ({ponto.uf}) · x {_decimal(ponto.x, 2)} · virada "
            f"{_decimal(ponto.y, 2)} p.p. · {format_integer(ponto.peso)} cédulas"
        )
        partes.append(
            f'<circle class="{_CLASSE_REGIAO.get(ponto.regiao, "r6")}" cx="{px(ponto.x):.1f}" '
            f'cy="{py(ponto.y):.1f}" r="{raio:.1f}"><title>{escape(dica)}</title></circle>'
        )
    if dispersao.inclinacao is not None and dispersao.intercepto is not None:
        partes.append(_reta(dispersao.inclinacao, dispersao.intercepto, x0, x1, y0, y1, px, py))
    partes.append(
        f'<line class="eixo" x1="{_MARGEM_ESQ}" x2="{_MARGEM_ESQ + largura}" '
        f'y1="{_MARGEM_TOPO + altura}" y2="{_MARGEM_TOPO + altura}"/>'
        f'<text x="{_MARGEM_ESQ + largura / 2:.0f}" y="{_ALTURA - 6}" text-anchor="middle">'
        f"{escape(eixo_x)}</text>"
        f'<text transform="translate(14 {_MARGEM_TOPO + altura / 2:.0f}) rotate(-90)" '
        'text-anchor="middle">virada (p.p.)</text>'
        "</svg>"
    )
    return "".join(partes)


def _reta(
    inclinacao: float,
    intercepto: float,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    px: _Escala,
    py: _Escala,
) -> str:
    """A reta recortada ao quadro, para não sair do gráfico."""
    xa, xb = x0, x1
    if inclinacao != 0:
        limites = sorted(((y0 - intercepto) / inclinacao, (y1 - intercepto) / inclinacao))
        xa, xb = max(x0, limites[0]), min(x1, limites[1])
    if xa >= xb:
        return ""
    ya, yb = intercepto + inclinacao * xa, intercepto + inclinacao * xb
    return (
        f'<line class="reta" x1="{px(xa):.1f}" y1="{py(ya):.1f}" '
        f'x2="{px(xb):.1f}" y2="{py(yb):.1f}"/>'
    )


def _grade(inicio: float, fim: float, escala: _Escala, *, horizontal: bool) -> list[str]:
    partes: list[str] = []
    for marca in _marcas(inicio, fim):
        posicao = escala(marca)
        rotulo = _decimal(marca, _casas(fim - inicio))
        if horizontal:
            base = _ALTURA - _MARGEM_BASE
            partes.append(
                f'<line class="grade" x1="{posicao:.1f}" x2="{posicao:.1f}" '
                f'y1="{_MARGEM_TOPO}" y2="{base}"/>'
                f'<text x="{posicao:.1f}" y="{base + 14}" text-anchor="middle">{rotulo}</text>'
            )
        else:
            partes.append(
                f'<line class="grade" x1="{_MARGEM_ESQ}" x2="{_LARGURA - _MARGEM_DIR}" '
                f'y1="{posicao:.1f}" y2="{posicao:.1f}"/>'
                f'<text x="{_MARGEM_ESQ - 6}" y="{posicao + 4:.1f}" text-anchor="end">'
                f"{rotulo}</text>"
            )
    return partes


def _faixa(valores: Sequence[float]) -> tuple[float, float]:
    """Do quantil 0,5% ao 99,5%, com folga de 5%. Faixa vazia ganha uma unidade."""
    ordenados = sorted(valores)
    corte = int(len(ordenados) * _CORTE)
    baixo = ordenados[corte]
    alto = ordenados[len(ordenados) - 1 - corte]
    if alto <= baixo:
        return baixo - 1, alto + 1
    folga = (alto - baixo) * 0.05
    return baixo - folga, alto + folga


def _marcas(inicio: float, fim: float) -> list[float]:
    passo = _passo(fim - inicio)
    primeira = math.ceil(inicio / passo) * passo
    marcas: list[float] = []
    atual = primeira
    while atual <= fim + 1e-9:
        marcas.append(0.0 if abs(atual) < passo * 1e-9 else atual)
        atual += passo
    return marcas


def _passo(amplitude: float) -> float:
    bruto = amplitude / 6
    potencia = 10.0 ** math.floor(math.log10(bruto))
    for fator in (1.0, 2.0, 5.0):
        if bruto <= fator * potencia:
            return fator * potencia
    return 10.0 * potencia


def _casas(amplitude: float) -> int:
    passo = _passo(amplitude)
    return max(0, -math.floor(math.log10(passo)))


def _explica_topo(origem: OrigemDosVotos) -> str:
    return (
        f'<p class="mudo">Os {len(origem.topo_a) or "até 20"} municípios de maior virada em cada '
        f"direção, entre os que tiveram ao menos {format_integer(MINIMO_DE_FINALISTAS)} votos "
        "de finalista em cada turno. Fontes em votos e em % das cédulas do 1º turno.</p>"
    )


def _tabela_topo(pagina: PaginaDaOrigem, municipios: Sequence[MunicipioOrigem]) -> str:
    if not municipios:
        return '<p class="mudo">Nenhum município passou do piso.</p>'
    a, b = pagina.origem.a, pagina.origem.b
    cabecalho = (
        '<th class="lugar">Município</th>'
        + _th("UF")
        + _th("Virada (p.p.)")
        + _th(f"Fatia do {a} 1º")
        + _th(f"Fatia do {a} 2º")
        + _th(f"Δ{a}")
        + _th(f"Δ{a} % votos 1º")
        + _th(f"Δ{b}")
        + _th(f"Δ{b} % votos 1º")
        + _th("O₁")
        + _th("O₁ % céd. 1º")
        + _th("−ΔBN")
        + _th("−ΔBN % céd. 1º")
        + _th("ΔC")
        + _th("ΔC % céd. 1º")
        + _th("Δ aptos")
        + _th("Resíduo")
    )
    linhas = "".join(_linha_topo(municipio) for municipio in municipios)
    return (
        '<div class="rolagem"><table class="ordenavel">'
        f"<thead><tr>{cabecalho}</tr></thead><tbody>{linhas}</tbody></table></div>"
    )


def _linha_topo(municipio: MunicipioOrigem) -> str:
    b = municipio.balanco
    cedulas = b.primeiro.cedulas
    return (
        "<tr>"
        f'<td class="lugar" data-ord="{escape(municipio.nome)}">{escape(municipio.nome)}</td>'
        f'<td data-ord="{escape(municipio.uf)}">{escape(municipio.uf)}</td>'
        + _pp(b.virada)
        + _share(b.primeiro.parte_de_a)
        + _share(b.segundo.parte_de_a)
        + _int(b.delta_a)
        + _frac(b.delta_a, b.primeiro.a)
        + _int(b.delta_b)
        + _frac(b.delta_b, b.primeiro.b)
        + _int(b.eliminados)
        + _frac(b.eliminados, cedulas)
        + _int(b.brancos_nulos_liberados)
        + _frac(b.brancos_nulos_liberados, cedulas)
        + _int(b.delta_comparecimento)
        + _frac(b.delta_comparecimento, cedulas)
        + _int(b.delta_aptos)
        + _int(b.residuo, falha=not b.fecha)
        + "</tr>"
    )


def _conferencia(pagina: PaginaDaOrigem) -> str:
    origem = pagina.origem
    falhas = origem.falhas
    partes = [
        f"<p>A identidade fecha em {format_integer(len(origem.municipios) - len(falhas))} de "
        f"{format_integer(len(origem.municipios))} municípios. "
        f"Não fecha em <strong>{format_integer(len(falhas))}</strong>.</p>"
    ]
    if falhas:
        ufs = ", ".join(f"{uf.uf} ({uf.falhas})" for uf in origem.ufs if uf.falhas)
        partes.append(
            f"<p>Por UF: {escape(ufs)}. Um resíduo concentrado em poucas UFs combina com "
            "boletins que chegaram depois de os lugares serem gravados; espalhado pelo país, "
            "aponta outro problema de dado. A coluna sobra é cédulas gravadas menos "
            "comparecimento do boletim.</p>"
        )
        partes.append(_tabela_falhas(falhas[:LIMITE_DE_FALHAS]))
        if len(falhas) > LIMITE_DE_FALHAS:
            partes.append(
                f'<p class="mudo">Mostrando {LIMITE_DE_FALHAS} de '
                f"{format_integer(len(falhas))}. O CSV ao lado traz todos.</p>"
            )
    partes.append(_ausentes("Só no 1º turno, numa UF que tem 2º turno", origem.so_no_primeiro))
    partes.append(_ausentes("Só no 2º turno", origem.so_no_segundo))
    partes.append(_ausentes("Sem comparecimento lido num dos turnos", origem.sem_comparecimento))
    return "".join(partes)


def _tabela_falhas(municipios: Sequence[MunicipioOrigem]) -> str:
    cabecalho = (
        '<th class="lugar">Município</th>'
        + _th("UF")
        + _th("Cédulas 1º")
        + _th("Comparecimento 1º")
        + _th("Sobra 1º")
        + _th("Cédulas 2º")
        + _th("Comparecimento 2º")
        + _th("Sobra 2º")
        + _th("O₂")
        + _th("Resíduo")
    )
    linhas = "".join(
        "<tr>"
        f'<td class="lugar" data-ord="{escape(m.nome)}">{escape(m.nome)}</td>'
        f'<td data-ord="{escape(m.uf)}">{escape(m.uf)}</td>'
        + _int(m.balanco.primeiro.cedulas)
        + _int(m.balanco.primeiro.comparecimento)
        + _int(m.balanco.primeiro.sobra)
        + _int(m.balanco.segundo.cedulas)
        + _int(m.balanco.segundo.comparecimento)
        + _int(m.balanco.segundo.sobra)
        + _int(m.balanco.segundo.outros)
        + _int(m.balanco.residuo, falha=True)
        + "</tr>"
        for m in municipios
    )
    return (
        '<div class="rolagem"><table class="ordenavel">'
        f"<thead><tr>{cabecalho}</tr></thead><tbody>{linhas}</tbody></table></div>"
    )


def _ausentes(titulo: str, lugares: Sequence[LugarAusente]) -> str:
    if not lugares:
        return f'<p class="mudo">{escape(titulo)}: nenhum.</p>'
    nomes = ", ".join(f"{lugar.nome} ({lugar.uf})" for lugar in lugares[:LIMITE_DE_AUSENTES])
    resto = len(lugares) - LIMITE_DE_AUSENTES
    if resto > 0:
        nomes += f" e mais {format_integer(resto)}"
    return f"<p>{escape(titulo)}: {format_integer(len(lugares))}. {escape(nomes)}.</p>"


def _th(rotulo: str) -> str:
    return f'<th class="num" aria-sort="none">{escape(rotulo)}</th>'


def _int(valor: int, *, falha: bool = False) -> str:
    classe = "num falha" if falha else "num"
    return f'<td class="{classe}" data-ord="{valor}">{format_integer(valor)}</td>'


def _frac(parte: int, todo: int) -> str:
    if todo == 0:
        return '<td class="num" data-ord="0">—</td>'
    razao = Fraction(parte, todo)
    return f'<td class="num" data-ord="{float(razao):.6f}">{format_percent(razao)}</td>'


def _share(valor: Fraction | None) -> str:
    if valor is None:
        return '<td class="num" data-ord="0">—</td>'
    return f'<td class="num" data-ord="{float(valor):.6f}">{format_percent(valor)}</td>'


def _pp(virada: Fraction | None) -> str:
    if virada is None:
        return '<td class="num" data-ord="0">—</td>'
    pontos = float(virada) * 100
    sinal = "+" if pontos > 0 else ""
    return f'<td class="num" data-ord="{pontos:.6f}">{sinal}{_decimal(pontos, 2)}</td>'


def _pct(parte: int, todo: int) -> str:
    if todo == 0:
        return "—"
    return format_percent(Fraction(parte, todo))


def _largura(parte: int, todo: int) -> str:
    return f"{max(0.0, parte / todo * 100):.2f}"


def _correlacao(valor: float | None) -> str:
    return "—" if valor is None else _decimal(valor, 3)


def _decimal(valor: float | None, casas: int) -> str:
    if valor is None:
        return "—"
    texto = f"{valor:.{casas}f}"
    if texto.lstrip("-").strip("0.") == "":
        texto = texto.lstrip("-")
    return texto.replace(".", ",")


def _cor(pagina: PaginaDaOrigem, numero: int) -> str:
    cor = pagina.cores.get(numero, COR_PADRAO)
    return cor if _HEX.fullmatch(cor) else COR_PADRAO


def _nome(pagina: PaginaDaOrigem, numero: int) -> str:
    sigla = pagina.siglas.get(numero)
    return f"{numero} ({sigla})" if sigla else str(numero)
