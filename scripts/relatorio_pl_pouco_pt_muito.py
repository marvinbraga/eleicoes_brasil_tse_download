"""Seções em que o PL teve poucos votos para presidente e o PT teve muitos.

Uso, na raiz do projeto:

    uv run python scripts/relatorio_pl_pouco_pt_muito.py --ano 2026 --sem-navegador

Lê os votos nominais de presidente já importados. O HTML sai em
relatorios/pl-pouco-pt-muito-{ano}.html e o CSV das seções que entram na regra
fica ao lado.
"""

from __future__ import annotations

import argparse
import csv
import sys
import webbrowser
from collections import Counter, defaultdict
from dataclasses import dataclass
from html import escape
from pathlib import Path

PL: int = 22
PT: int = 13
VEZES: int = 10
PISO: int = 50
ATE: int = 30
TOPO: int = 40


@dataclass(frozen=True, slots=True)
class Secao:
    turno: int
    uf: str
    municipio: int
    zona: int
    secao: int
    pl: int
    pt: int

    @property
    def chave(self) -> tuple[str, int, int, int]:
        return (self.uf, self.municipio, self.zona, self.secao)


def muitos(pl: int, pt: int) -> bool:
    """PT com pelo menos 50 votos e pelo menos dez vezes o PL."""
    return pt >= PISO and pt >= VEZES * pl


def mediana(valores: list[int]) -> int:
    return valores[(len(valores) - 1) // 2]


def percentil(valores: list[int], parte: int) -> int:
    indice = max(0, (parte * len(valores)) // 10 - 1)
    return valores[indice]


@dataclass(frozen=True, slots=True)
class Degrau:
    votos_pl: int | None
    secoes: int
    mediana_pt: int
    p90_pt: int
    maximo_pt: int
    muitos: int


def escada(secoes: list[Secao]) -> tuple[Degrau, ...]:
    grupos: dict[int | None, list[int]] = defaultdict(list)
    for secao in secoes:
        grupos[secao.pl if secao.pl <= ATE else None].append(secao.pt)
    degraus: list[Degrau] = []
    for votos in (*range(ATE + 1), None):
        pts = sorted(grupos.get(votos, []))
        if not pts:
            degraus.append(Degrau(votos, 0, 0, 0, 0, 0))
            continue
        if votos is None:
            contados = sum(1 for secao in secoes if secao.pl > ATE and muitos(secao.pl, secao.pt))
        else:
            contados = sum(1 for pt in pts if muitos(votos, pt))
        degraus.append(Degrau(votos, len(pts), mediana(pts), percentil(pts, 9), pts[-1], contados))
    return tuple(degraus)


def _milhar(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def _pct(parte: int, total: int) -> str:
    if total == 0:
        return "0,00%"
    texto = f"{100 * parte / total:.2f}".replace(".", ",")
    return f"{texto}%"


def _rotulo(votos: int | None) -> str:
    if votos is None:
        return f"{ATE + 1} ou mais"
    return str(votos)


_COR_1 = "#3d9a98"
_COR_2 = "#e0b15a"
_COR_TINTA = "#f5f5f5"
_COR_MUDO = "#c8c8c8"
_COR_GRADE = "#333333"
_LARGURA = 720
_ALTURA = 280

_ESTILO = """
:root { color-scheme: dark; --fundo: #171717; --tinta: #f5f5f5; --linha: #333;
  --marca: #0d6f6e; }
body { margin: 0; background: var(--fundo); color: var(--tinta);
  font: 16px/1.5 "Segoe UI", sans-serif; }
main { max-width: 1100px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }
h1 { font-size: 1.7rem; font-weight: 650; margin: 0 0 0.75rem; }
h2 { font-size: 1.2rem; font-weight: 650; margin: 2.2rem 0 0.6rem; }
p { max-width: 44rem; }
.indice { display: flex; flex-wrap: wrap; gap: 0.6rem 1.2rem; margin: 0 0 0.5rem; }
.indice a { color: #8fd0ce; }
.exemplo { border-left: 3px solid var(--marca); padding-left: 0.8rem; }
table { border-collapse: collapse; width: 100%; margin: 0.5rem 0 2rem;
  font-variant-numeric: tabular-nums; }
th, td { border-bottom: 1px solid var(--linha); padding: 0.35rem 0.5rem;
  text-align: right; }
th:first-child, td:first-child, td.nome { text-align: left; }
th { position: sticky; top: 0; background: var(--fundo); }
table.escada th { position: static; }
th.grupo { text-align: center; }
th.turno, td.turno { border-left: 2px solid #555; }
caption { text-align: left; font-weight: 650; padding-bottom: 0.4rem; }
.nota { color: #c8c8c8; font-size: 0.92rem; }
figure { margin: 1rem 0 1.5rem; }
figcaption { font-weight: 650; margin-bottom: 0.4rem; }
svg { width: 100%; height: auto; background: #141414; border: 1px solid var(--linha);
  border-radius: 8px; }
.legenda { display: flex; flex-wrap: wrap; gap: 0.75rem 1.25rem; margin: 0.45rem 0 0;
  color: #c8c8c8; font-size: 0.92rem; }
.amostra { display: inline-block; width: 0.8rem; height: 0.8rem; border-radius: 2px;
  margin-right: 0.35rem; vertical-align: -1px; }
"""


def _piso_do_pl(votos: int) -> int:
    return max(PISO, VEZES * votos)


def _teto_eixo(maior: float) -> float:
    if maior <= 0:
        return 1.0
    passo = 10 ** max(0, len(str(int(maior))) - 2)
    teto = passo
    while teto < maior:
        teto += passo
    return float(teto)


def _numero_eixo(valor: float, sufixo: str) -> str:
    if abs(valor - round(valor)) < 0.05:
        texto = _milhar(int(round(valor)))
    else:
        texto = f"{valor:.1f}".replace(".", ",")
    return f"{texto}{sufixo}"


def _legenda(itens: list[tuple[str, str]]) -> str:
    pedacos = "".join(
        f'<span><i class="amostra" style="background:{cor}"></i>{escape(nome)}</span>'
        for nome, cor in itens
    )
    return f'<p class="legenda">{pedacos}</p>'


def _legenda_turnos() -> str:
    return _legenda((("1º turno", _COR_1), ("2º turno", _COR_2)))


def _figura(titulo_id: str, titulo: str, desenho: str, nota: str, legenda: str) -> str:
    return (
        "<figure>\n"
        f'<figcaption id="{titulo_id}">{escape(titulo)}</figcaption>\n'
        f"{desenho}\n"
        f"{legenda}\n"
        f'<p class="nota">{escape(nota)}</p>\n'
        "</figure>\n"
    )


def _moldura(
    titulo_id: str,
    teto: float,
    sufixo: str,
    *,
    baixo: int = 40,
) -> tuple[str, float, float, float, float]:
    esquerda, direita, topo = 56.0, 16.0, 16.0
    largura_plot = _LARGURA - esquerda - direita
    altura_plot = _ALTURA - topo - baixo
    partes = [
        f'<svg viewBox="0 0 {_LARGURA} {_ALTURA}" role="img" aria-labelledby="{titulo_id}">',
    ]
    for marca in (0, 0.5, 1):
        y = topo + altura_plot - marca * altura_plot
        partes.append(
            f'<line x1="{esquerda:.1f}" y1="{y:.1f}" x2="{esquerda + largura_plot:.1f}" '
            f'y2="{y:.1f}" stroke="{_COR_GRADE}"/>'
        )
        partes.append(
            f'<text x="{esquerda - 8:.1f}" y="{y + 4:.1f}" text-anchor="end" '
            f'fill="{_COR_MUDO}" font-size="12">'
            f"{escape(_numero_eixo(teto * marca, sufixo))}</text>"
        )
    return "\n".join(partes), esquerda, topo, largura_plot, altura_plot


def _x_degrau(indice: int, total: int, esquerda: float, largura: float) -> float:
    if total <= 1:
        return esquerda + largura / 2
    return esquerda + (indice + 0.5) * (largura / total)


def _linhas(
    titulo_id: str,
    rotulos: list[str],
    primeiro: list[float],
    segundo: list[float],
    *,
    teto: float | None = None,
    sufixo: str = "",
) -> str:
    maior = max([*primeiro, *segundo], default=0)
    topo_eixo = _teto_eixo(maior) if teto is None else teto
    fragmento, esquerda, topo, largura, altura_plot = _moldura(titulo_id, topo_eixo, sufixo)
    partes = [fragmento]
    total = len(rotulos)
    for indice, rotulo in enumerate(rotulos):
        if total > 12 and indice % 5 != 0 and indice != total - 1:
            continue
        x = _x_degrau(indice, total, esquerda, largura)
        partes.append(
            f'<text x="{x:.1f}" y="{topo + altura_plot + 22:.1f}" text-anchor="middle" '
            f'fill="{_COR_MUDO}" font-size="12">{escape(rotulo)}</text>'
        )
    for valores, cor in ((primeiro, _COR_1), (segundo, _COR_2)):
        partes.append(_traco(valores, cor, total, esquerda, topo, largura, altura_plot, topo_eixo))
    partes.append("</svg>")
    return "\n".join(partes)


def _traco(
    valores: list[float],
    cor: str,
    total: int,
    esquerda: float,
    topo: float,
    largura: float,
    altura_plot: float,
    topo_eixo: float,
) -> str:
    pontos: list[str] = []
    circulos: list[str] = []
    for indice, valor in enumerate(valores):
        x = _x_degrau(indice, total, esquerda, largura)
        y = topo + altura_plot - (valor / topo_eixo) * altura_plot
        pontos.append(f"{x:.1f},{y:.1f}")
        circulos.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{cor}"/>')
    linha = f'<polyline fill="none" stroke="{cor}" stroke-width="2.5" points="{" ".join(pontos)}"/>'
    return linha + "".join(circulos)


def _barras(titulo_id: str, itens: list[tuple[str, float, str]]) -> str:
    maior = max(valor for _, valor, _ in itens)
    teto = _teto_eixo(maior * 1.2)
    fragmento, esquerda, topo, largura, altura_plot = _moldura(titulo_id, teto, "")
    partes = [fragmento]
    faixa = largura / len(itens)
    largura_barra = min(36.0, faixa * 0.55)
    for indice, (rotulo, valor, cor) in enumerate(itens):
        x = esquerda + indice * faixa + (faixa - largura_barra) / 2
        altura = (valor / teto) * altura_plot
        y = topo + altura_plot - altura
        partes.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{largura_barra:.1f}" height="{altura:.1f}" '
            f'fill="{cor}"/>'
        )
        partes.append(
            f'<text x="{x + largura_barra / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle" '
            f'fill="{_COR_TINTA}" font-size="12">{escape(_milhar(int(valor)))}</text>'
        )
        partes.append(
            f'<text x="{x + largura_barra / 2:.1f}" y="{topo + altura_plot + 22:.1f}" '
            f'text-anchor="middle" fill="{_COR_MUDO}" font-size="12">{escape(rotulo)}</text>'
        )
    partes.append("</svg>")
    return "\n".join(partes)


def _barras_uf(
    titulo_id: str,
    ufs: list[str],
    primeiro: list[int],
    segundo: list[int],
) -> str:
    teto = _teto_eixo(float(max([*primeiro, *segundo], default=0)))
    topo, baixo, esquerda, direita = 12.0, 28.0, 40.0, 16.0
    altura_linha = 26
    largura = 720
    altura = int(topo + baixo + altura_linha * max(len(ufs), 1))
    largura_plot = largura - esquerda - direita
    partes = [
        f'<svg viewBox="0 0 {largura} {altura}" role="img" aria-labelledby="{titulo_id}">',
    ]
    for marca in (0, 0.5, 1):
        x = esquerda + marca * largura_plot
        partes.append(
            f'<line x1="{x:.1f}" y1="{topo:.1f}" x2="{x:.1f}" y2="{altura - baixo:.1f}" '
            f'stroke="{_COR_GRADE}"/>'
        )
        partes.append(
            f'<text x="{x:.1f}" y="{altura - 8}" text-anchor="middle" fill="{_COR_MUDO}" '
            f'font-size="12">{escape(_numero_eixo(teto * marca, ""))}</text>'
        )
    for indice, uf in enumerate(ufs):
        y = topo + indice * altura_linha
        partes.append(
            f'<text x="{esquerda - 8:.1f}" y="{y + 16:.1f}" text-anchor="end" '
            f'fill="{_COR_TINTA}" font-size="12">{escape(uf)}</text>'
        )
        partes.append(
            _par_de_barras(esquerda, y, largura_plot, teto, primeiro[indice], segundo[indice])
        )
    partes.append("</svg>")
    return "\n".join(partes)


def _par_de_barras(
    esquerda: float,
    y: float,
    largura_plot: float,
    teto: float,
    um: int,
    dois: int,
) -> str:
    pedacos: list[str] = []
    for valor, cor, deslocamento in ((um, _COR_1, 3), (dois, _COR_2, 13)):
        comprimento = 0 if teto == 0 else (valor / teto) * largura_plot
        pedacos.append(
            f'<rect x="{esquerda:.1f}" y="{y + deslocamento:.1f}" width="{comprimento:.1f}" '
            f'height="8" fill="{cor}"/>'
        )
    return "".join(pedacos)


def _exatos(degraus: tuple[Degrau, ...]) -> tuple[Degrau, ...]:
    return tuple(degrau for degrau in degraus if degrau.votos_pl is not None)


def _fatia(degrau: Degrau) -> float:
    if degrau.secoes == 0:
        return 0.0
    return 100 * degrau.muitos / degrau.secoes


def _cai_abaixo(degraus: tuple[Degrau, ...]) -> Degrau | None:
    exatos = [degrau for degrau in _exatos(degraus) if degrau.secoes]
    for indice, degrau in enumerate(exatos):
        if _fatia(degrau) >= 10:
            continue
        if all(_fatia(item) < 10 for item in exatos[indice:]):
            return degrau
    return None


def _exemplo_regra() -> str:
    um = VEZES * 1
    seis = VEZES * 6
    return (
        f"Com 1 voto do PL, {VEZES} vezes 1 é {um}. O piso é {PISO}, então o PT entra "
        f"a partir de {max(um, PISO)} votos. Com 6 votos do PL, {VEZES} vezes 6 é {seis}, "
        f"então o PT entra a partir de {max(seis, PISO)} votos. Com nenhum voto do PL, "
        f"o PT entra a partir de {_piso_do_pl(0)} votos."
    )


def _leitura_degrau(degraus: tuple[Degrau, ...], votos: int, turno: int) -> str:
    degrau = _degrau(degraus, votos)
    unidade = "voto" if votos == 1 else "votos"
    return (
        f"No {turno}º turno, {_milhar(degrau.secoes)} seções tiveram exatamente "
        f"{votos} {unidade} do PL. A mediana do PT nessas seções foi "
        f"{_milhar(degrau.mediana_pt)}. Dessas, {_milhar(degrau.muitos)} passaram na regra."
    )


def _frase_queda(degrau: Degrau | None, turno: int) -> str:
    if degrau is None or degrau.votos_pl is None:
        return ""
    return (
        f"No {turno}º turno, a partir de {degrau.votos_pl} votos do PL, menos de 10% "
        f"das seções do degrau entram na regra ({_milhar(degrau.muitos)} de "
        f"{_milhar(degrau.secoes)})."
    )


def _indice() -> str:
    return """<nav class="indice" aria-label="Partes do relatório">
<a href="#regra">A pergunta</a>
<a href="#conta">A regra</a>
<a href="#quantas">Quantas seções</a>
<a href="#escada">A escada</a>
<a href="#mediana">A mediana</a>
<a href="#ufs">Por estado</a>
<a href="#exemplos">Exemplos</a>
<a href="#limites">O que não diz</a>
</nav>"""


def _introducao(
    ano: int,
    total_1: int,
    total_2: int,
    muitos_1: int,
    muitos_2: int,
    repetidas: int,
    inverso_1: int,
    inverso_2: int,
) -> str:
    return f"""<h1>PL com poucos votos e PT com muitos, {ano}</h1>
{_indice()}
<h2 id="regra">O que a página responde</h2>
<p>A pergunta é uma só. Em quais seções o PL teve poucos votos para presidente
e, na mesma seção, o PT teve muitos? A página responde isso no 1º turno e no 2º turno.</p>
<p>Seção é o lugar da urna: uma UF, um município, uma zona e um número de seção.
Os votos contados são os nominais do PT, número 13, e do PL, número 22.</p>
<h2 id="conta">O que conta como muitos</h2>
<p>Muitos, nesta página, é uma regra fixa. O PT precisa ter pelo menos {PISO} votos
e pelo menos {VEZES} vezes os votos do PL naquela seção.
A conta não muda de seção para seção.</p>
<p class="exemplo">{_exemplo_regra()}</p>
<p>O inverso troca os partidos e usa a mesma conta: PT com poucos votos e PL com muitos.</p>
<p>Entrar nos dois turnos significa a mesma seção nas duas votações:
mesma UF, mesmo município, mesma zona e o mesmo número.
Não significa que os votos tenham sido iguais.</p>
<p>No 1º turno havia outros candidatos. PL mais PT não é o total de votos válidos da seção.
No 2º turno só restaram os dois, então PL mais PT é praticamente esse total.</p>
<h2 id="quantas">Quantas seções entram</h2>
<p>Houve nos dois turnos. No 1º turno, {_milhar(muitos_1)} de {_milhar(total_1)} seções
({_pct(muitos_1, total_1)}) entram na regra. No 2º turno, {_milhar(muitos_2)} de
{_milhar(total_2)} ({_pct(muitos_2, total_2)}). {_milhar(repetidas)} seções entram
nos dois turnos. O inverso, PT com poucos votos e PL com muitos, foi
{_milhar(inverso_1)} seções no 1º turno e {_milhar(inverso_2)} no 2º.</p>
"""


def _painel_contagem(
    muitos_1: int,
    muitos_2: int,
    repetidas: int,
    inverso_1: int,
    inverso_2: int,
) -> str:
    desenho = _barras(
        "grafico-contagem",
        [
            ("Regra, 1º", float(muitos_1), _COR_1),
            ("Regra, 2º", float(muitos_2), _COR_2),
            ("Nos dois", float(repetidas), "#8fd0ce"),
            ("Inverso, 1º", float(inverso_1), "#8a8a8a"),
            ("Inverso, 2º", float(inverso_2), "#b0b0b0"),
        ],
    )
    return _figura(
        "grafico-contagem",
        "Seções que entram na regra, e o inverso",
        desenho,
        (
            "Regra é PT alto e PL baixo. Inverso é PL alto e PT baixo. "
            "Nos dois é a mesma seção nas duas votações."
        ),
        _legenda(
            (
                ("Regra, 1º turno", _COR_1),
                ("Regra, 2º turno", _COR_2),
                ("Nos dois turnos", "#8fd0ce"),
                ("Inverso, 1º turno", "#8a8a8a"),
                ("Inverso, 2º turno", "#b0b0b0"),
            )
        ),
    )


def _painel_escada(escada_1: tuple[Degrau, ...], escada_2: tuple[Degrau, ...]) -> str:
    rotulos = [str(degrau.votos_pl) for degrau in _exatos(escada_1)]
    na_regra = _linhas(
        "grafico-escada",
        rotulos,
        [float(degrau.muitos) for degrau in _exatos(escada_1)],
        [float(degrau.muitos) for degrau in _exatos(escada_2)],
    )
    fatias = _linhas(
        "grafico-fatia",
        rotulos,
        [_fatia(degrau) for degrau in _exatos(escada_1)],
        [_fatia(degrau) for degrau in _exatos(escada_2)],
        teto=100,
        sufixo="%",
    )
    leituras = " ".join(
        _leitura_degrau(escada, votos, turno)
        for turno, escada in ((1, escada_1), (2, escada_2))
        for votos in (1, 2, 3)
    )
    queda = " ".join(
        _frase_queda(_cai_abaixo(escada), turno) for turno, escada in ((1, escada_1), (2, escada_2))
    )
    return f"""<h2 id="escada">A escada, voto a voto</h2>
<p>Cada degrau reúne as seções em que o PL teve exatamente aquele número de votos, de 0 até 30.
O gráfico de baixo usa só esses degraus. O degrau “31 ou mais” fica na tabela,
porque mistura quantidades diferentes de votos do PL.</p>
<p>Seções é quantas urnas tiveram exatamente aqueles votos do PL, qualquer que tenha sido o PT.
Mediana do PT é o valor do meio dessa lista.
9 em 10 é o valor abaixo do qual ficam nove décimos dessas seções.
Máximo é o maior voto do PT no degrau.
Na regra é quantas dessas seções também passaram no piso de {PISO} votos
e nas {VEZES} vezes.</p>
<p>{leituras}</p>
<p>{queda}</p>
{_figura(
    "grafico-escada",
    "Seções na regra, para cada quantidade de votos do PL",
    na_regra,
    (
        "O eixo de baixo é o número exato de votos do PL. "
        "A altura é quantas seções daquele degrau passaram na regra."
    ),
    _legenda_turnos(),
)}
{_figura(
    "grafico-fatia",
    "Fatia do degrau que entra na regra",
    fatias,
    (
        "Cem por cento seria todas as seções daquele degrau. "
        "A fatia cai quando o PL deixa de ser pouco diante do PT."
    ),
    _legenda_turnos(),
)}
"""


def _exemplo_linha(escada_1: tuple[Degrau, ...], escada_2: tuple[Degrau, ...]) -> str:
    um = _degrau(escada_1, 1)
    dois = _degrau(escada_2, 1)
    fora = um.secoes - um.muitos
    return (
        "<p class=\"exemplo\">Como ler a linha 1. "
        "Ela não é uma cidade. Junta todas as seções do país em que o PL teve exatamente 1 voto. "
        f"No 1º turno foram {_milhar(um.secoes)} seções, com o PT alto ou baixo. "
        "Ordenando o voto do PT dessas seções, o do meio foi "
        f"{_milhar(um.mediana_pt)}: metade teve o PT nesse valor ou abaixo. "
        f"Em 9 de cada 10, o PT ficou em {_milhar(um.p90_pt)} ou menos. "
        f"A seção com mais votos do PT teve {_milhar(um.maximo_pt)}. "
        f"Das {_milhar(um.secoes)}, {_milhar(um.muitos)} também passaram na regra, "
        f"porque o PT teve pelo menos {_piso_do_pl(1)} votos. "
        f"As outras {fora} ficaram de fora. "
        f"No 2º turno a mesma linha repete a conta: {_milhar(dois.secoes)} seções, "
        f"PT do meio {_milhar(dois.mediana_pt)}, "
        f"9 em 10 até {_milhar(dois.p90_pt)}, "
        f"maior PT {_milhar(dois.maximo_pt)}, "
        f"e {_milhar(dois.muitos)} na regra.</p>"
    )


def _tabela_escada(escada_1: tuple[Degrau, ...], escada_2: tuple[Degrau, ...]) -> str:
    linhas = "\n".join(_linha_degrau(a, b) for a, b in zip(escada_1, escada_2, strict=True))
    return f"""{_exemplo_linha(escada_1, escada_2)}
<table class="escada">
<caption>Uma linha para cada quantidade de votos do PL</caption>
<thead>
<tr>
<th rowspan="2">Votos do PL na seção</th>
<th class="grupo" colspan="5">1º turno</th>
<th class="grupo turno" colspan="5">2º turno</th>
</tr>
<tr>
<th>Seções com esse voto do PL</th>
<th>PT do meio</th>
<th>PT de 9 em 10</th>
<th>Maior PT</th>
<th>Seções na regra</th>
<th class="turno">Seções com esse voto do PL</th>
<th>PT do meio</th>
<th>PT de 9 em 10</th>
<th>Maior PT</th>
<th>Seções na regra</th>
</tr>
</thead>
<tbody>
{linhas}
</tbody>
</table>
<p class="nota">A linha 0 é a seção em que o PL não teve voto nominal.
PT do meio olha todas as seções da linha, também as que não entram na regra.
“31 ou mais” junta seções com mais de 30 votos do PL e aplica a regra com o número real.</p>
"""


def _painel_mediana(escada_1: tuple[Degrau, ...], escada_2: tuple[Degrau, ...]) -> str:
    rotulos = [str(degrau.votos_pl) for degrau in _exatos(escada_1)]
    desenho = _linhas(
        "grafico-mediana",
        rotulos,
        [float(degrau.mediana_pt) for degrau in _exatos(escada_1)],
        [float(degrau.mediana_pt) for degrau in _exatos(escada_2)],
    )
    return (
        '<h2 id="mediana">A mediana do PT</h2>\n'
        "<p>Quando o PL teve exatamente 1 voto, a mediana do PT foi "
        f"{_celula(escada_1, 1)} no 1º turno e {_celula(escada_2, 1)} no 2º. "
        f"Com 2 votos do PL, as medianas foram {_celula(escada_1, 2)} e {_celula(escada_2, 2)}. "
        f"Com 3, {_celula(escada_1, 3)} e {_celula(escada_2, 3)}. "
        "Esse meio da lista não é o corte da regra. Uma seção com a mediana pode ficar fora "
        f"ou dentro do piso de {PISO} votos.</p>\n"
        + _figura(
            "grafico-mediana",
            "Mediana dos votos do PT em cada degrau do PL",
            desenho,
            (
                "Cada ponto é o meio da lista de votos do PT "
                "nas seções com exatamente aqueles votos do PL."
            ),
            _legenda_turnos(),
        )
    )


def _painel_ufs(por_turno: dict[int, list[Secao]]) -> str:
    ufs, primeiro, segundo = _contagem_ufs(por_turno)
    desenho = _barras_uf(
        "grafico-ufs",
        ufs,
        [primeiro[uf] for uf in ufs],
        [segundo[uf] for uf in ufs],
    )
    return (
        '<h2 id="ufs">Onde essas seções estão</h2>\n'
        "<p>O gráfico conta seções que passaram na regra, por estado. "
        "A ordem é a do 1º turno, da maior quantidade para a menor. "
        "A concentração descreve onde esse desenho de voto apareceu. "
        "Ela não aponta irregularidade.</p>\n"
        + _figura(
            "grafico-ufs",
            "Seções na regra, por UF",
            desenho,
            (
                "Em cada estado, a barra de cima é o 1º turno e a de baixo é o 2º. "
                "O número exato está na tabela."
            ),
            _legenda_turnos(),
        )
        + _tabela_ufs(por_turno)
    )


def _painel_exemplos(
    primeiro: list[Secao],
    segundo: list[Secao],
    nomes: dict[tuple[str, int], str],
) -> str:
    return (
        '<h2 id="exemplos">Exemplos de seções</h2>\n'
        "<p>As duas tabelas não são a lista inteira. "
        f"São as {TOPO} seções de cada turno com até 10 votos do PL e pelo menos 100 do PT, "
        "ordenadas pelo voto do PT. Servem para ver o caso extremo. "
        "Toda seção que entra na regra está no CSV gravado ao lado deste HTML.</p>\n"
        + _tabela_topo(primeiro, nomes, 1)
        + _tabela_topo(segundo, nomes, 2)
    )


def _fecho() -> str:
    return """<h2 id="limites">O que a contagem não diz</h2>
<p>A contagem não prova irregularidade, erro de urna nem fraude.
Ela descreve o desenho do voto nessas seções.</p>
<p>Os votos vêm de raw.boletim, cargo presidente, tipo nominal, números 13 e 22.
Seção sem linha daquele número conta zero.
Cada seção tem uma só eleição gravada, então o voto não foi somado duas vezes.
Branco e nulo ficam de fora. O comparecimento não entra nesta leitura.</p>
"""


def html_do_relatorio(
    ano: int,
    por_turno: dict[int, list[Secao]],
    nomes: dict[tuple[str, int], str],
    repetidas: int,
) -> str:
    primeiro = por_turno[1]
    segundo = por_turno[2]
    muitos_1 = sum(1 for secao in primeiro if muitos(secao.pl, secao.pt))
    muitos_2 = sum(1 for secao in segundo if muitos(secao.pl, secao.pt))
    inverso_1 = sum(1 for secao in primeiro if muitos(secao.pt, secao.pl))
    inverso_2 = sum(1 for secao in segundo if muitos(secao.pt, secao.pl))
    escada_1 = escada(primeiro)
    escada_2 = escada(segundo)
    corpo = "\n".join(
        (
            _introducao(
                ano,
                len(primeiro),
                len(segundo),
                muitos_1,
                muitos_2,
                repetidas,
                inverso_1,
                inverso_2,
            ),
            _painel_contagem(muitos_1, muitos_2, repetidas, inverso_1, inverso_2),
            _painel_escada(escada_1, escada_2),
            _tabela_escada(escada_1, escada_2),
            _painel_mediana(escada_1, escada_2),
            _painel_ufs(por_turno),
            _painel_exemplos(primeiro, segundo, nomes),
            _fecho(),
        )
    )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>PL com poucos votos e PT com muitos — {ano}</title>\n"
        f"<style>{_ESTILO}</style>\n</head>\n<body>\n<main>\n{corpo}\n</main>\n"
        "</body>\n</html>\n"
    )


def _degrau(degraus: tuple[Degrau, ...], votos: int) -> Degrau:
    for degrau in degraus:
        if degrau.votos_pl == votos:
            return degrau
    raise KeyError(votos)


def _celula(degraus: tuple[Degrau, ...], votos: int) -> str:
    return _milhar(_degrau(degraus, votos).mediana_pt)


def _linha_degrau(primeiro: Degrau, segundo: Degrau) -> str:
    return (
        "<tr>"
        f"<td>{escape(_rotulo(primeiro.votos_pl))}</td>"
        f"{_nums(primeiro)}{_nums(segundo, separar=True)}"
        "</tr>"
    )


def _nums(degrau: Degrau, *, separar: bool = False) -> str:
    marca = ' class="turno"' if separar else ""
    if degrau.secoes == 0:
        return f"<td{marca}>0</td><td>—</td><td>—</td><td>—</td><td>0</td>"
    return (
        f"<td{marca}>{_milhar(degrau.secoes)}</td>"
        f"<td>{_milhar(degrau.mediana_pt)}</td>"
        f"<td>{_milhar(degrau.p90_pt)}</td>"
        f"<td>{_milhar(degrau.maximo_pt)}</td>"
        f"<td>{_milhar(degrau.muitos)}</td>"
    )


def _contagem_ufs(
    por_turno: dict[int, list[Secao]],
) -> tuple[list[str], Counter[str], Counter[str]]:
    contagem = {
        turno: Counter(secao.uf for secao in secoes if muitos(secao.pl, secao.pt))
        for turno, secoes in por_turno.items()
    }
    ufs = sorted(set(contagem[1]) | set(contagem[2]), key=lambda uf: (-contagem[1][uf], uf))
    presentes = [uf for uf in ufs if contagem[1][uf] or contagem[2][uf]]
    return presentes, contagem[1], contagem[2]


def _tabela_ufs(por_turno: dict[int, list[Secao]]) -> str:
    ufs, primeiro, segundo = _contagem_ufs(por_turno)
    linhas = "\n".join(
        "<tr>"
        f"<td>{escape(uf)}</td>"
        f"<td>{_milhar(primeiro[uf])}</td>"
        f"<td>{_milhar(segundo[uf])}</td>"
        "</tr>"
        for uf in ufs
    )
    return f"""<table>
<caption>Seções na regra, por UF</caption>
<thead><tr><th>UF</th><th>1º turno</th><th>2º turno</th></tr></thead>
<tbody>
{linhas}
</tbody>
</table>
"""


def _tabela_topo(secoes: list[Secao], nomes: dict[tuple[str, int], str], turno: int) -> str:
    escolhidas = sorted(
        (secao for secao in secoes if secao.pl <= 10 and secao.pt >= 100),
        key=lambda secao: (-secao.pt, secao.pl, secao.uf, secao.municipio, secao.zona, secao.secao),
    )[:TOPO]
    linhas = "\n".join(_linha_secao(secao, nomes) for secao in escolhidas)
    return f"""<table>
<caption>{turno}º turno — {TOPO} seções com até 10 votos do PL e pelo menos 100 do PT</caption>
<thead><tr><th>Lugar</th><th>Zona</th><th>Seção</th><th>PL</th><th>PT</th></tr></thead>
<tbody>
{linhas}
</tbody>
</table>
"""


def _linha_secao(secao: Secao, nomes: dict[tuple[str, int], str]) -> str:
    nome = nomes.get((secao.uf, secao.municipio), str(secao.municipio))
    lugar = f"{nome} ({secao.uf})"
    return (
        "<tr>"
        f'<td class="nome">{escape(lugar)}</td>'
        f"<td>{secao.zona}</td><td>{secao.secao}</td>"
        f"<td>{secao.pl}</td><td>{_milhar(secao.pt)}</td>"
        "</tr>"
    )


def _ordem_secao(secao: Secao) -> tuple[str, int, int, int]:
    return (secao.uf, secao.municipio, secao.zona, secao.secao)


def gravar_csv(
    caminho: Path,
    por_turno: dict[int, list[Secao]],
    nomes: dict[tuple[str, int], str],
    repetidas: set[tuple[str, int, int, int]],
) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(
            [
                "turno",
                "uf",
                "municipio",
                "nome",
                "zona",
                "secao",
                "votos_pl",
                "votos_pt",
                "nos_dois_turnos",
            ]
        )
        for turno in (1, 2):
            ordenadas = sorted(por_turno[turno], key=_ordem_secao)
            for secao in ordenadas:
                if not muitos(secao.pl, secao.pt):
                    continue
                writer.writerow(
                    [
                        turno,
                        secao.uf,
                        secao.municipio,
                        nomes.get((secao.uf, secao.municipio), str(secao.municipio)),
                        secao.zona,
                        secao.secao,
                        secao.pl,
                        secao.pt,
                        "sim" if secao.chave in repetidas else "nao",
                    ]
                )


def ler_csv(caminho: Path) -> list[Secao]:
    secoes: list[Secao] = []
    with caminho.open(encoding="utf-8", newline="") as handle:
        for turno, uf, municipio, zona, secao, pl, pt, *_resto in csv.reader(handle):
            secoes.append(
                Secao(int(turno), uf, int(municipio), int(zona), int(secao), int(pl), int(pt))
            )
    return secoes


def ler_nomes(caminho: Path) -> dict[tuple[str, int], str]:
    nomes: dict[tuple[str, int], str] = {}
    with caminho.open(encoding="utf-8", newline="") as handle:
        for uf, codigo, nome in csv.reader(handle):
            nomes[(uf, int(codigo))] = nome
    return nomes


def ler_banco(ano: int) -> tuple[list[Secao], dict[tuple[str, int], str]]:
    raiz = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(raiz / "src"))
    from eleicoes.adapters.postgres_sink import connect_postgres
    from eleicoes.composition.correspondencia import _host_settings

    conexao = connect_postgres(_host_settings(_ambiente()))
    try:
        with conexao.cursor() as cursor:
            cursor.execute(
                """
                SELECT turno, uf, municipio, zona, secao,
                       COALESCE(SUM(quantidade) FILTER (
                           WHERE tipo_voto = 'nominal' AND numero = %s), 0)::int,
                       COALESCE(SUM(quantidade) FILTER (
                           WHERE tipo_voto = 'nominal' AND numero = %s), 0)::int
                FROM raw.boletim
                WHERE ano = %s AND cargo = 'presidente' AND turno IN (1, 2)
                GROUP BY turno, uf, municipio, zona, secao
                """,
                (PL, PT, ano),
            )
            secoes = [
                Secao(int(turno), uf, int(municipio), int(zona), int(secao), int(pl), int(pt))
                for turno, uf, municipio, zona, secao, pl, pt in cursor.fetchall()
            ]
            cursor.execute(
                """
                SELECT DISTINCT uf, codigo, split_part(nome, ' (', 1)
                FROM analise.relatorio_presidente_governador_linha
                WHERE ano = %s AND turno = 1 AND cargo = 'presidente'
                """,
                (ano,),
            )
            nomes = {(uf, int(codigo)): nome for uf, codigo, nome in cursor.fetchall()}
    finally:
        conexao.close()
    return secoes, nomes


def _ambiente() -> dict[str, str]:
    import os

    from dotenv import load_dotenv

    load_dotenv()
    return dict(os.environ)


def _repetidas(por_turno: dict[int, list[Secao]]) -> set[tuple[str, int, int, int]]:
    no_primeiro = {secao.chave for secao in por_turno[1] if muitos(secao.pl, secao.pt)}
    return {
        secao.chave
        for secao in por_turno[2]
        if muitos(secao.pl, secao.pt) and secao.chave in no_primeiro
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seções com PL baixo e PT alto.")
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--csv", type=Path, help="CSV agregado turno,uf,municipio,zona,secao,pl,pt")
    parser.add_argument("--nomes", type=Path, help="CSV de nomes: uf,codigo,nome")
    parser.add_argument("--destino", type=Path)
    parser.add_argument("--sem-navegador", action="store_true")
    args = parser.parse_args(argv)
    if (args.csv is None) != (args.nomes is None):
        print("Informe --csv e --nomes juntos, ou nenhum dos dois.", file=sys.stderr)
        return 1
    if args.csv is None:
        secoes, nomes = ler_banco(args.ano)
    else:
        secoes, nomes = ler_csv(args.csv), ler_nomes(args.nomes)
    por_turno = {
        1: [secao for secao in secoes if secao.turno == 1],
        2: [secao for secao in secoes if secao.turno == 2],
    }
    if not por_turno[1] or not por_turno[2]:
        print("Faltam seções de presidente no 1º ou no 2º turno.", file=sys.stderr)
        return 1
    repetidas = _repetidas(por_turno)
    destino = args.destino or Path("relatorios") / f"pl-pouco-pt-muito-{args.ano}.html"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        html_do_relatorio(args.ano, por_turno, nomes, len(repetidas)),
        encoding="utf-8",
    )
    gravar_csv(destino.with_suffix(".csv"), por_turno, nomes, repetidas)
    print(f"Relatório gravado em {destino}")
    print(f"Seções na regra: {destino.with_suffix('.csv')}")
    if not args.sem_navegador:
        webbrowser.open(destino.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
