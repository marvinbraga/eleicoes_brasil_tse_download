"""HTML das regiões e do porte dos municípios: 1º × 2º turno de presidente.

A página não busca nada fora dela: estilo, script e logos vão embutidos. O tema
segue o sistema; ``?tema=light`` ou ``?tema=dark`` no endereço manda nele.
"""

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from fractions import Fraction
from html import escape
from typing import Final

from eleicoes.domain.mapa import Marca
from eleicoes.domain.percentual import format_integer, format_percent, round_half_up
from eleicoes.domain.regioes_porte import (
    EXTERIOR,
    LinhaGrupo,
    RegioesEPorte,
    parte_do_ganho_de_a,
)
from eleicoes.domain.values import uf_name

TITULO: Final = "Regiões e porte dos municípios"
COMANDO_DO_RELATORIO_GRAVADO: Final = (
    "uv run python scripts/relatorio_presidente_governador.py --ano {ano} --turno 2 --atualizar"
)
_COR_A: Final = "#b8505a"
_COR_B: Final = "#4e6f95"
_ESCALA_CSS: Final = 10_000
_MINIMO_PARA_ROTULO: Final = Fraction(9, 100)
_TRAVESSAO: Final = "—"
_Unidade = Callable[[LinhaGrupo], str]
_ESTILO: Final = """
:root {
  color-scheme: light;
  --fundo: #ffffff; --painel: #f5f6f7; --texto: #15191c; --mudo: #5a646d;
  --linha: #d7dce0; --eixo: #8a949c; --aviso: #fff7e0; --aviso-borda: #e0b54a;
}
:root[data-tema="dark"] {
  color-scheme: dark;
  --fundo: #0a0a0a; --painel: #171717; --texto: #f2f4f5; --mudo: #a3adb5;
  --linha: #2e3438; --eixo: #6d7780; --aviso: #2a2412; --aviso-borda: #8a6d1c;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-tema="light"]) {
    color-scheme: dark;
    --fundo: #0a0a0a; --painel: #171717; --texto: #f2f4f5; --mudo: #a3adb5;
    --linha: #2e3438; --eixo: #6d7780; --aviso: #2a2412; --aviso-borda: #8a6d1c;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--fundo); color: var(--texto);
  font-family: "Segoe UI", "Noto Sans", "Liberation Sans", "DejaVu Sans", sans-serif;
  font-size: 15px; line-height: 1.45;
}
main { max-width: 1200px; margin-inline: auto; padding: 1.5rem 16px 3rem; }
h1 { font-size: clamp(1.5rem, 3vw, 2.1rem); margin: 0 0 .25rem; letter-spacing: -0.02em; }
h2 { font-size: 1.35rem; margin: 2.5rem 0 .25rem; }
h3 { font-size: 1.05rem; margin: 1.75rem 0 .5rem; }
p { max-width: 75ch; }
.subtitulo, .explica { color: var(--mudo); }
.legenda { display: flex; flex-wrap: wrap; gap: 1rem; margin: 1rem 0; }
.partido { display: inline-flex; align-items: center; gap: .4rem; font-weight: 600; }
.partido img { width: 28px; height: 28px; object-fit: contain; }
.amostra { width: 14px; height: 14px; border-radius: 3px; display: inline-block; }
.aviso {
  background: var(--aviso); border: 1px solid var(--aviso-borda); border-radius: 8px;
  padding: .75rem 1rem; margin: 1rem 0; max-width: 80ch;
}
.aviso p { margin: .25rem 0; }
code { font-size: .85em; overflow-wrap: anywhere; }
.grafico { display: grid; gap: .35rem; }
.linha {
  display: grid; align-items: center; gap: .5rem 1rem;
  grid-template-columns: minmax(8rem, 12rem) minmax(0, 3fr) minmax(0, 2fr);
  padding: .4rem 0; border-top: 1px solid var(--linha);
}
.variacao .linha { grid-template-columns: minmax(8rem, 12rem) repeat(3, minmax(0, 1fr)); }
.linha.cabeca { border-top: 0; color: var(--mudo); font-size: .85rem; padding-bottom: 0; }
.linha.total { border-top: 2px solid var(--texto); }
.rotulo strong { display: block; }
.rotulo span, .valor, .votos { color: var(--mudo); font-size: .85rem; }
.pilha {
  display: flex; height: 1.6rem; border-radius: 4px; overflow: hidden;
  background: var(--painel);
}
.fatia {
  display: flex; align-items: center; justify-content: center; min-width: 0;
  color: #ffffff; font-weight: 600; font-size: .8rem; white-space: nowrap;
  text-shadow: 0 1px 1px rgba(0, 0, 0, .45);
}
.votos { display: flex; justify-content: space-between; gap: .5rem; margin-top: .15rem; }
.diverge { position: relative; height: 1.1rem; background: var(--painel); border-radius: 3px; }
.diverge .eixo {
  position: absolute; left: 50%; top: -3px; bottom: -3px; width: 1px; background: var(--eixo);
}
.diverge .barra { position: absolute; top: 0; bottom: 0; border-radius: 2px; }
.valor { margin-top: .15rem; font-variant-numeric: tabular-nums; }
.tabela { overflow-x: auto; margin-top: 1rem; border: 1px solid var(--linha); border-radius: 8px; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
th, td { padding: .35rem .6rem; border-bottom: 1px solid var(--linha); white-space: nowrap; }
th { background: var(--painel); font-weight: 600; font-size: .85rem; text-align: right; }
td { text-align: right; }
th:first-child, td:first-child {
  text-align: left; position: sticky; left: 0; background: var(--fundo);
}
th:first-child { background: var(--painel); }
tr.total td { font-weight: 600; border-top: 2px solid var(--texto); }
.notas { margin: 2.5rem 0 0; padding: 1rem 0 0 1.2rem; border-top: 1px solid var(--linha);
  color: var(--mudo); max-width: 80ch; }
.notas li { margin-bottom: .4rem; }
@media (max-width: 720px) {
  .linha, .variacao .linha { grid-template-columns: minmax(0, 1fr); gap: .3rem; }
  .linha.cabeca { display: none; }
  .titulo-celula { display: block; color: var(--mudo); font-size: .8rem; }
}
@media (min-width: 721px) { .titulo-celula { display: none; } }
"""
_SCRIPT_TEMA: Final = """
<script>
(function () {
  var tema = new URLSearchParams(window.location.search).get("tema");
  if (tema === "light" || tema === "dark") {
    document.documentElement.setAttribute("data-tema", tema);
  }
})();
</script>
"""


def html_de_regioes_e_porte(
    ano: int, gerado_em: datetime, leitura: RegioesEPorte, marcas: Mapping[int, Marca]
) -> str:
    rotulos = _Rotulos(leitura, marcas)
    momento = gerado_em.astimezone().strftime("%Y-%m-%d %H:%M")
    subtitulo = (
        f"Presidente {ano} · 1º × 2º turno · {rotulos.b} × {rotulos.a}"
        f" · só municípios gravados nos dois turnos · gerado em {momento}"
    )
    corpo = (
        f"<h1>{escape(TITULO)}</h1>"
        f'<p class="subtitulo">{escape(subtitulo)}</p>'
        + _legenda(leitura, marcas)
        + _aviso(leitura)
        + _secao(
            "regioes",
            "Por região",
            "Cada macrorregião soma os municípios das suas UFs; o exterior fica à parte.",
            leitura.regioes,
            leitura.brasil,
            rotulos,
            unidade=_unidade_da_regiao,
        )
        + _secao(
            "porte",
            "Por porte do município",
            "Porte pelo eleitorado apto do 1º turno. O exterior não entra; o total é o "
            "Brasil sem o exterior.",
            leitura.portes,
            leitura.brasil_sem_exterior,
            rotulos,
            unidade=_unidade_do_porte,
        )
        + _notas(leitura, rotulos)
    )
    return (
        "<!DOCTYPE html>"
        '<html lang="pt-BR">'
        "<head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(TITULO)}</title>"
        f"{_SCRIPT_TEMA}"
        f"<style>{_ESTILO}{_cores(leitura, marcas)}</style>"
        "</head><body>"
        f"<main>{corpo}</main>"
        "</body></html>"
    )


class _Rotulos:
    def __init__(self, leitura: RegioesEPorte, marcas: Mapping[int, Marca]) -> None:
        self.a = _nome_do_partido(leitura.a, marcas)
        self.b = _nome_do_partido(leitura.b, marcas)
        self.numero_a = str(leitura.a)
        self.numero_b = str(leitura.b)


def _nome_do_partido(numero: int, marcas: Mapping[int, Marca]) -> str:
    marca = marcas.get(numero)
    if marca is None or not marca.sigla:
        return str(numero)
    return f"{numero} {marca.sigla}"


def _cores(leitura: RegioesEPorte, marcas: Mapping[int, Marca]) -> str:
    cor_a = _cor(marcas.get(leitura.a), _COR_A)
    cor_b = _cor(marcas.get(leitura.b), _COR_B)
    return f":root {{ --cor-a: {cor_a}; --cor-b: {cor_b}; }}"


def _cor(marca: Marca | None, padrao: str) -> str:
    if marca is None:
        return padrao
    return escape(marca.cor)


def _legenda(leitura: RegioesEPorte, marcas: Mapping[int, Marca]) -> str:
    itens = (
        _partido(leitura.b, "var(--cor-b)", marcas),
        _partido(leitura.a, "var(--cor-a)", marcas),
    )
    return f'<div class="legenda">{"".join(itens)}</div>'


def _partido(numero: int, cor: str, marcas: Mapping[int, Marca]) -> str:
    marca = marcas.get(numero)
    nome = escape(_nome_do_partido(numero, marcas))
    if marca is not None and marca.logo:
        figura = f'<img src="{escape(marca.logo)}" alt="">'
    else:
        figura = f'<span class="amostra" style="background:{cor}"></span>'
    return f'<span class="partido">{figura}{nome}</span>'


def _aviso(leitura: RegioesEPorte) -> str:
    if not leitura.sem_segundo_turno:
        return ""
    faltam = _lista_de_ufs(leitura.sem_segundo_turno)
    partes = [
        f"<p><strong>Ainda sem 2º turno no relatório gravado:</strong> {escape(faltam)}. "
        "As regiões e as faixas de porte ficam sem os municípios delas.</p>"
    ]
    if leitura.fora_do_relatorio:
        nos_boletins = _lista_de_ufs(leitura.fora_do_relatorio)
        comando = COMANDO_DO_RELATORIO_GRAVADO.format(ano=leitura.ano)
        partes.append(
            f"<p>Os boletins já têm 2º turno de {escape(nos_boletins)}, mas o relatório "
            f"gravado ainda não. Para incluir, regrave o 2º turno: <code>{escape(comando)}"
            "</code>.</p>"
        )
    return f'<div class="aviso" role="note">{"".join(partes)}</div>'


def _lista_de_ufs(ufs: Sequence[str]) -> str:
    nomes = [f"{uf_name(uf)} ({uf})" for uf in ufs]
    if len(nomes) == 1:
        return nomes[0]
    return ", ".join(nomes[:-1]) + " e " + nomes[-1]


def _unidade_da_regiao(linha: LinhaGrupo) -> str:
    if linha.chave == "Exterior":
        return _plural(linha.municipios, "cidade", "cidades")
    return _plural(linha.municipios, "município", "municípios")


def _unidade_do_porte(linha: LinhaGrupo) -> str:
    return _plural(linha.municipios, "município", "municípios")


def _plural(quantidade: int, singular: str, plural: str) -> str:
    return f"{format_integer(quantidade)} {singular if quantidade == 1 else plural}"


def _secao(
    ancora: str,
    titulo: str,
    explicacao: str,
    linhas: tuple[LinhaGrupo, ...],
    total: LinhaGrupo,
    rotulos: _Rotulos,
    *,
    unidade: _Unidade,
) -> str:
    todas = (*linhas, total)
    return (
        f'<section id="{ancora}" aria-labelledby="{ancora}-titulo">'
        f'<h2 id="{ancora}-titulo">{escape(titulo)}</h2>'
        f'<p class="explica">{escape(explicacao)}</p>'
        "<h3>2º turno</h3>"
        + _grafico_do_segundo(todas, rotulos, unidade)
        + "<h3>Do 1º para o 2º turno: onde o "
        + escape(rotulos.numero_a)
        + " cresceu</h3>"
        + _grafico_da_variacao(todas, rotulos, unidade)
        + "<h3>Números</h3>"
        + _tabela(linhas, total, rotulos)
        + "</section>"
    )


def _grafico_do_segundo(
    linhas: tuple[LinhaGrupo, ...], rotulos: _Rotulos, unidade: _Unidade
) -> str:
    maior = max((abs(linha.diferenca) for linha in linhas), default=0)
    cabeca = (
        '<div class="linha cabeca" aria-hidden="true"><span></span>'
        f"<span>Fatia dos válidos: {escape(rotulos.b)} | {escape(rotulos.a)}</span>"
        f"<span>Diferença em votos ({escape(rotulos.numero_a)} − "
        f"{escape(rotulos.numero_b)})</span></div>"
    )
    corpo = "".join(
        _linha_do_segundo(linha, rotulos, unidade, maior, total=indice == len(linhas) - 1)
        for indice, linha in enumerate(linhas)
    )
    return f'<div class="grafico segundo">{cabeca}{corpo}</div>'


def _linha_do_segundo(
    linha: LinhaGrupo, rotulos: _Rotulos, unidade: _Unidade, maior: int, *, total: bool
) -> str:
    segundo = linha.segundo
    descricao = (
        f"{linha.rotulo}: {rotulos.b} {format_percent(segundo.fatia_b)}"
        f" ({format_integer(segundo.b)} votos); {rotulos.a} {format_percent(segundo.fatia_a)}"
        f" ({format_integer(segundo.a)} votos)"
    )
    pilha = (
        f'<div class="pilha" role="img" aria-label="{escape(descricao)}">'
        f"{_fatia(segundo.fatia_b, 'var(--cor-b)')}{_fatia(segundo.fatia_a, 'var(--cor-a)')}"
        "</div>"
        '<div class="votos">'
        f"<span>{escape(rotulos.numero_b)}: {format_integer(segundo.b)}</span>"
        f"<span>{escape(rotulos.numero_a)}: {format_integer(segundo.a)}</span>"
        "</div>"
    )
    diferenca = linha.diferenca
    frente = _quem_lidera(diferenca, rotulos)
    rotulo_diferenca = f"{_com_sinal(diferenca)} votos{frente}"
    return (
        f'<div class="linha{" total" if total else ""}">'
        f"{_rotulo(linha, unidade)}"
        f'<div><span class="titulo-celula">Fatia dos válidos</span>{pilha}</div>'
        '<div><span class="titulo-celula">Diferença em votos</span>'
        f"{_divergente(Fraction(diferenca), Fraction(maior), rotulo_diferenca)}</div>"
        "</div>"
    )


def _quem_lidera(diferenca: int, rotulos: _Rotulos) -> str:
    if diferenca > 0:
        return f" · {rotulos.numero_a} à frente"
    if diferenca < 0:
        return f" · {rotulos.numero_b} à frente"
    return ""


def _grafico_da_variacao(
    linhas: tuple[LinhaGrupo, ...], rotulos: _Rotulos, unidade: _Unidade
) -> str:
    maior_voto = max(
        (abs(valor) for linha in linhas for valor in (linha.variacao_a, linha.variacao_b)),
        default=0,
    )
    maior_virada = max((abs(linha.virada) for linha in linhas), default=Fraction(0))
    cabeca = (
        '<div class="linha cabeca" aria-hidden="true"><span></span>'
        f"<span>Variação de votos do {escape(rotulos.numero_b)}</span>"
        f"<span>Variação de votos do {escape(rotulos.numero_a)}</span>"
        f"<span>Virada do {escape(rotulos.numero_a)} entre os dois (p.p.)</span></div>"
    )
    corpo = "".join(
        _linha_da_variacao(
            linha,
            rotulos,
            unidade,
            Fraction(maior_voto),
            maior_virada,
            total=indice == len(linhas) - 1,
        )
        for indice, linha in enumerate(linhas)
    )
    return f'<div class="grafico variacao">{cabeca}{corpo}</div>'


def _linha_da_variacao(
    linha: LinhaGrupo,
    rotulos: _Rotulos,
    unidade: _Unidade,
    maior_voto: Fraction,
    maior_virada: Fraction,
    *,
    total: bool,
) -> str:
    ganho_b = f"{_com_sinal(linha.variacao_b)} ({_percentual_com_sinal(linha.variacao_relativa_b)})"
    ganho_a = f"{_com_sinal(linha.variacao_a)} ({_percentual_com_sinal(linha.variacao_relativa_a)})"
    return (
        f'<div class="linha{" total" if total else ""}">'
        f"{_rotulo(linha, unidade)}"
        f'<div><span class="titulo-celula">Variação do {escape(rotulos.numero_b)}</span>'
        f"{_divergente(Fraction(linha.variacao_b), maior_voto, ganho_b, 'var(--cor-b)')}</div>"
        f'<div><span class="titulo-celula">Variação do {escape(rotulos.numero_a)}</span>'
        f"{_divergente(Fraction(linha.variacao_a), maior_voto, ganho_a, 'var(--cor-a)')}</div>"
        f'<div><span class="titulo-celula">Virada do {escape(rotulos.numero_a)}</span>'
        f"{_divergente(linha.virada, maior_virada, _pontos(linha.virada))}</div>"
        "</div>"
    )


def _rotulo(linha: LinhaGrupo, unidade: _Unidade) -> str:
    return (
        f'<div class="rotulo"><strong>{escape(linha.rotulo)}</strong>'
        f"<span>{escape(unidade(linha))}</span></div>"
    )


def _fatia(fatia: Fraction, cor: str) -> str:
    largura = _largura(fatia)
    texto = format_percent(fatia) if fatia >= _MINIMO_PARA_ROTULO else ""
    return (
        f'<div class="fatia" style="width:{largura}%;background:{cor}">'
        f"<span>{escape(texto)}</span></div>"
    )


def _divergente(valor: Fraction, maior: Fraction, rotulo: str, cor: str | None = None) -> str:
    """Barra a partir do meio: para a direita favorece A; para a esquerda, B."""
    meia = Fraction(0) if maior == 0 else abs(valor) / maior / 2
    largura = _largura(meia)
    if cor is None:
        cor = "var(--cor-a)" if valor >= 0 else "var(--cor-b)"
    lado = "left:50%" if valor >= 0 else f"left:{_largura(Fraction(1, 2) - meia)}%"
    return (
        f'<div class="diverge" role="img" aria-label="{escape(rotulo)}">'
        '<div class="eixo"></div>'
        f'<div class="barra" style="{lado};width:{largura}%;background:{cor}"></div>'
        "</div>"
        f'<div class="valor">{escape(rotulo)}</div>'
    )


def _largura(fatia: Fraction) -> str:
    centesimos = round_half_up(fatia * _ESCALA_CSS)
    inteiro, resto = divmod(max(centesimos, 0), 100)
    return f"{inteiro}.{resto:02d}"


def _tabela(linhas: tuple[LinhaGrupo, ...], total: LinhaGrupo, rotulos: _Rotulos) -> str:
    a = escape(rotulos.numero_a)
    b = escape(rotulos.numero_b)
    cabecas = (
        "Grupo",
        "Municípios",
        f"{b} 1º turno",
        f"{a} 1º turno",
        f"{b} 2º turno",
        f"{a} 2º turno",
        f"{b} % válidos 2º",
        f"{a} % válidos 2º",
        f"Diferença ({a} − {b})",
        f"Variação {b}",
        f"Variação {b} %",
        f"Variação {a}",
        f"Variação {a} %",
        f"{a} entre os dois, 1º",
        f"{a} entre os dois, 2º",
        f"Virada do {a}",
        f"Parte do ganho do {a}",
    )
    cabeca = "".join(f'<th scope="col">{rotulo}</th>' for rotulo in cabecas)
    corpo = "".join(_linha_da_tabela(linha, total) for linha in linhas)
    corpo += _linha_da_tabela(total, total, classe=' class="total"')
    return (
        '<div class="tabela"><table>'
        f"<thead><tr>{cabeca}</tr></thead><tbody>{corpo}</tbody></table></div>"
    )


def _linha_da_tabela(linha: LinhaGrupo, total: LinhaGrupo, classe: str = "") -> str:
    celulas = (
        format_integer(linha.municipios),
        format_integer(linha.primeiro.b),
        format_integer(linha.primeiro.a),
        format_integer(linha.segundo.b),
        format_integer(linha.segundo.a),
        format_percent(linha.segundo.fatia_b),
        format_percent(linha.segundo.fatia_a),
        _com_sinal(linha.diferenca),
        _com_sinal(linha.variacao_b),
        _percentual_com_sinal(linha.variacao_relativa_b),
        _com_sinal(linha.variacao_a),
        _percentual_com_sinal(linha.variacao_relativa_a),
        format_percent(linha.primeiro.fatia_a_no_par),
        format_percent(linha.segundo.fatia_a_no_par),
        _pontos(linha.virada),
        _percentual_ou_traco(parte_do_ganho_de_a(linha, total)),
    )
    dados = "".join(f"<td>{escape(celula)}</td>" for celula in celulas)
    return f'<tr{classe}><th scope="row">{escape(linha.rotulo)}</th>{dados}</tr>'


def _com_sinal(valor: int) -> str:
    sinal = "+" if valor > 0 else ""
    return sinal + format_integer(valor)


def _percentual_com_sinal(valor: Fraction | None) -> str:
    if valor is None:
        return _TRAVESSAO
    sinal = "+" if valor > 0 else ""
    return sinal + format_percent(valor)


def _percentual_ou_traco(valor: Fraction | None) -> str:
    if valor is None:
        return _TRAVESSAO
    return format_percent(valor)


def _pontos(valor: Fraction) -> str:
    return _percentual_com_sinal(valor).removesuffix("%") + " p.p."


def _notas(leitura: RegioesEPorte, rotulos: _Rotulos) -> str:
    itens = "".join(f"<li>{escape(nota)}</li>" for nota in notas(leitura, rotulos.a, rotulos.b))
    return f'<ul class="notas">{itens}</ul>'


def notas(leitura: RegioesEPorte, a: str, b: str) -> tuple[str, ...]:
    numero_a = str(leitura.a)
    numero_b = str(leitura.b)
    found = [
        "Os votos vêm do relatório presidente × governador gravado no banco, município a "
        "município. Só entram os municípios gravados nos dois turnos; seções que ainda não "
        "chegaram ao banco no 2º turno deixam os números do município menores.",
        "Municípios das UFs que já têm 2º turno gravados só no 1º, deixados de fora: "
        f"{format_integer(leitura.so_no_primeiro)}.",
        f"As fatias do 2º turno são sobre os votos válidos. A diferença é votos do {a} menos "
        f"votos do {b}: a barra para a direita põe o {numero_a} à frente; para a esquerda, "
        f"o {numero_b}.",
        "A variação compara os votos de cada finalista no 2º turno com os do 1º, nos mesmos "
        "municípios. A variação em % tem o 1º turno como base.",
        f"A virada é a fatia do {numero_a} só entre os votos dos dois finalistas, "
        f"{numero_a} / ({numero_a} + {numero_b}), no 2º turno menos a mesma conta no 1º, em "
        f"pontos percentuais. Positiva: o {numero_a} cresceu, em proporção, mais que o "
        f"{numero_b}.",
        f"A parte do ganho do {numero_a} é a variação de votos dele no grupo sobre a variação "
        "no total da tabela.",
        "O porte é o eleitorado apto do 1º turno, somado das seções do boletim de urna. As "
        "faixas fecham em cima: 10.000 aptos é “até 10 mil”, 10.001 já é “de 10 mil a 50 mil”. "
        "O exterior não tem porte e só aparece nas regiões.",
    ]
    if leitura.sem_eleitorado:
        found.append(
            "Municípios pareados sem eleitorado apto nos boletins, fora do porte: "
            f"{format_integer(leitura.sem_eleitorado)}."
        )
    if EXTERIOR in leitura.sem_segundo_turno:
        found.append("O exterior ainda não tem 2º turno gravado e não aparece nas regiões.")
    return tuple(found)
