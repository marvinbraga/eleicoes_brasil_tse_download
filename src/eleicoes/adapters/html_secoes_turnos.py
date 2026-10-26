"""HTML do 1º × 2º turno seção por seção: z por cenário e verificações objetivas."""

from datetime import datetime
from fractions import Fraction
from html import escape
from typing import Final

from eleicoes.adapters.html_tema import render_page
from eleicoes.domain.anomalia_secao import (
    ACIMA_DOS_APTOS,
    ALERTAS,
    APTOS_MUDARAM,
    CEDULAS_DESTOANTES,
    DIFERENCA_MINIMA_DE_APTOS,
    DIFERENCA_MINIMA_DE_CEDULAS,
    GRUPO_MUNICIPIO,
    GRUPO_NENHUM,
    GRUPO_UF,
    GRUPO_ZONA,
    VARIACAO_DE_APTOS,
    VARIACAO_DE_CEDULAS,
    AnaliseSecoes,
    ContagemCenario,
    FaixaDeVotos,
    ResumoUf,
    SecaoTurnos,
    com_alerta,
    destaques,
)
from eleicoes.domain.mapa_turnos import (
    FORA_A,
    FORA_B,
    LIMIAR_FORA,
    LIMIAR_MODERADO,
    MODERADO,
    Cenario,
    Leitura,
)
from eleicoes.domain.percentual import format_integer, format_percent, round_half_up
from eleicoes.domain.values import UF_CODES

TITULO: Final = "Seções no 1º × 2º turno"
CENARIO_INICIAL: Final = "proporcional"
_SORT_SCALE: Final = 1_000_000
_TABLE_OPEN: Final = (
    '<div class="table-responsive grade-scroll"><table class="table table-sm grade">'
)
_TABLE_CLOSE: Final = "</table></div>"
_ROTULOS_ALERTA: Final[dict[str, str]] = {
    ACIMA_DOS_APTOS: "Cédulas acima dos aptos",
    CEDULAS_DESTOANTES: "Cédulas mudaram muito",
    APTOS_MUDARAM: "Aptos mudaram",
}
_ROTULOS_GRUPO: Final[dict[str, str]] = {
    GRUPO_MUNICIPIO: "município",
    GRUPO_ZONA: "zona",
    GRUPO_UF: "UF",
    GRUPO_NENHUM: "sem base",
}
_ROTULOS_CLASSE: Final[dict[str, str]] = {
    FORA_A: "|z| > 3,5, a favor de A",
    FORA_B: "|z| > 3,5, a favor de B",
    MODERADO: "2 < |z| ≤ 3,5",
}
_ESTILO: Final = """
<style>
.controles { display: flex; flex-wrap: wrap; gap: 1rem; align-items: end; margin: 1rem 0; }
.controles label { display: flex; flex-direction: column; gap: .25rem; color: var(--mudo); }
.controles select { min-width: 14rem; }
.oculto { display: none !important; }
h2 { font-size: 1.3rem; margin-top: 2rem; }
.aviso { max-width: 80ch; color: var(--mudo); }
</style>
"""
_SCRIPT: Final = """
<script>
(function () {
  var cenario = document.getElementById("cenario");
  var uf = document.getElementById("uf");
  var contador = document.getElementById("exibidas");

  function aplicar() {
    document.querySelectorAll("[data-cenario]").forEach(function (bloco) {
      bloco.classList.toggle("oculto", bloco.getAttribute("data-cenario") !== cenario.value);
    });
    var vistas = 0;
    document.querySelectorAll("tr[data-uf]").forEach(function (linha) {
      var escondida = uf.value !== "" && linha.getAttribute("data-uf") !== uf.value;
      linha.classList.toggle("oculto", escondida);
      var bloco = linha.closest("[data-cenario]");
      var visivel = bloco !== null && !bloco.classList.contains("oculto");
      if (!escondida && visivel && linha.hasAttribute("data-destaque")) {
        vistas += 1;
      }
    });
    contador.textContent = String(vistas);
  }

  cenario.addEventListener("change", aplicar);
  uf.addEventListener("change", aplicar);
  aplicar();
})();
</script>
"""


def html_das_secoes(ano: int, gerado_em: datetime, analise: AnaliseSecoes) -> str:
    ufs = ", ".join(resumo.uf for resumo in analise.resumos)
    momento = gerado_em.astimezone().strftime("%Y-%m-%d %H:%M")
    subtitle = escape(
        f"Presidente {ano} · finalistas {analise.a} (A) e {analise.b} (B)"
        f" · UFs com 2º turno no banco: {ufs} · gerado em {momento}"
    )
    body = (
        _ESTILO
        + _abertura(analise)
        + _controles(analise)
        + "<h2>Resumo por UF</h2>"
        + "".join(_resumos(analise, indice) for indice in range(len(analise.cenarios)))
        + "<h2>Seções de maior |z|</h2>"
        + _explica_destaques(analise)
        + "".join(_destaques(analise, indice) for indice in range(len(analise.cenarios)))
        + "<h2>Verificações objetivas</h2>"
        + _verificacoes(analise)
        + "<h2>|z| > 3,5 por tamanho da seção</h2>"
        + "".join(_faixas(analise, indice) for indice in range(len(analise.cenarios)))
        + _SCRIPT
    )
    return render_page(TITULO, subtitle, body, notas(analise))


def notas(analise: AnaliseSecoes) -> tuple[str, ...]:
    variacao = format_percent(VARIACAO_DE_CEDULAS)
    aptos = format_percent(VARIACAO_DE_APTOS)
    return (
        "As seções se pareiam por UF, município, zona e número da seção. Seção que só aparece "
        "num dos turnos (renumerada, agregada ou ainda não carregada) entra só na contagem.",
        "Cédulas da seção são os votos de presidente nominais, brancos e nulos do boletim. "
        "O comparecimento gravado no boletim não entra nas contas.",
        "Cada cenário redistribui só os votos dos eliminados do 1º turno. A fatia esperada de A "
        "é (A₁ + f·O₁) / (A₁ + B₁ + O₁); a real é A₂ / (A₂ + B₂). O resíduo é real menos "
        "esperada; os votos de diferença são o resíduo vezes os votos de finalista do 2º turno.",
        "O z robusto é (resíduo − mediana do grupo) / (MAD / 0,6745), como no mapa por "
        "município. O grupo é o município; se ele tiver menos de "
        f"{analise.minimo} seções comparáveis, a zona; se a zona também tiver, a UF.",
        f"Só entra no z a seção com ao menos {analise.piso} votos válidos no 1º turno e "
        f"{analise.piso} votos de finalista no 2º. O MAD não olha o tamanho da seção, e "
        "nas pequenas o acaso sozinho leva o z para as caudas; a tabela por tamanho mostra "
        "quanto disso ainda sobra acima do piso.",
        f"Com dezenas de milhares de seções, |z| > {_numero(LIMIAR_FORA)} aparece por acaso. "
        "O esperado ao lado de cada contagem é o número de seções vezes a chance de uma normal "
        "passar do limiar. O z robusto só segue a normal se os resíduos seguirem; observado "
        "acima do esperado reflete sobretudo caudas mais pesadas que a normal.",
        "Os cenários testam as mesmas seções, então as contagens deles andam juntas. "
        "Não some as contagens de cenários diferentes.",
        "As verificações objetivas não dependem de cenário: cédulas acima dos eleitores aptos, "
        f"cédulas que mudam mais de {variacao} entre os turnos (e ao menos "
        f"{DIFERENCA_MINIMA_DE_CEDULAS}), e aptos que mudam mais de {aptos} (e ao menos "
        f"{DIFERENCA_MINIMA_DE_APTOS}). Aptos que mudam indicam seção agregada ou cadastro "
        "alterado, e então as cédulas mudam junto.",
        "z alto e verificação que falha não provam fraude nem erro de apuração. Apontam "
        "seções para olhar com o boletim na mão.",
    )


def _abertura(analise: AnaliseSecoes) -> str:
    total = analise.total
    return (
        f"<p>{format_integer(total.pareadas)} seções pareadas. "
        f"Só no 1º turno: {format_integer(total.so_no_primeiro)}. "
        f"Só no 2º turno: {format_integer(total.so_no_segundo)}. "
        f"Abaixo do piso de {analise.piso} votos: {format_integer(total.abaixo_do_piso)}.</p>"
        '<p class="aviso">Desvio grande não prova nada sobre a apuração: só aponta onde o '
        "cenário explica mal o voto da seção, perto das vizinhas.</p>"
    )


def _controles(analise: AnaliseSecoes) -> str:
    opcoes = "".join(_opcao_cenario(cenario) for cenario in analise.cenarios)
    ufs = "".join(
        f'<option value="{escape(resumo.uf)}">{escape(resumo.nome)} ({escape(resumo.uf)})</option>'
        for resumo in analise.resumos
    )
    return (
        '<div class="controles">'
        '<label>Cenário dos eliminados<select id="cenario" class="form-select form-select-sm">'
        f"{opcoes}</select></label>"
        '<label>UF<select id="uf" class="form-select form-select-sm">'
        f'<option value="">Todas as UFs</option>{ufs}</select></label>'
        '<p class="mb-0">Seções em destaque exibidas: <strong id="exibidas">0</strong></p>'
        "</div>"
    )


def _opcao_cenario(cenario: Cenario) -> str:
    selected = " selected" if cenario.chave == CENARIO_INICIAL else ""
    return f'<option value="{escape(cenario.chave)}"{selected}>{escape(cenario.rotulo)}</option>'


def _bloco(analise: AnaliseSecoes, indice: int, conteudo: str) -> str:
    cenario = analise.cenarios[indice]
    return (
        f'<div data-cenario="{escape(cenario.chave)}">'
        f'<p class="aviso">{escape(cenario.descricao)}</p>{conteudo}</div>'
    )


def _resumos(analise: AnaliseSecoes, indice: int) -> str:
    head = _head(
        ("UF", "lugar"),
        ("Pareadas", "num"),
        ("Só no 1º", "num"),
        ("Só no 2º", "num"),
        ("Abaixo do piso", "num"),
        ("Com z", "num"),
        (f"|z| > {_numero(LIMIAR_FORA)}", "num"),
        ("Esperado", "num"),
        (f"|z| > {_numero(LIMIAR_MODERADO)}", "num"),
        ("Esperado", "num"),
        (_ROTULOS_ALERTA[ACIMA_DOS_APTOS], "num"),
        (_ROTULOS_ALERTA[CEDULAS_DESTOANTES], "num"),
        (_ROTULOS_ALERTA[APTOS_MUDARAM], "num"),
    )
    linhas = "".join(_resumo(resumo, indice) for resumo in (*analise.resumos, analise.total))
    return _bloco(analise, indice, f"{_TABLE_OPEN}{head}<tbody>{linhas}</tbody>{_TABLE_CLOSE}")


def _resumo(resumo: ResumoUf, indice: int) -> str:
    contagem: ContagemCenario = resumo.cenarios[indice]
    nome = escape(resumo.nome if not resumo.uf else f"{resumo.nome} ({resumo.uf})")
    alertas = "".join(_inteiro(valor) for valor in resumo.alertas)
    return (
        "<tr>"
        f'<td class="lugar" data-ord="{nome}">{nome}</td>'
        f"{_inteiro(resumo.pareadas)}{_inteiro(resumo.so_no_primeiro)}"
        f"{_inteiro(resumo.so_no_segundo)}{_inteiro(resumo.abaixo_do_piso)}"
        f"{_inteiro(contagem.com_z)}{_inteiro(contagem.fora)}"
        f"{_decimal(contagem.fora_esperado)}{_inteiro(contagem.acima_de_dois)}"
        f"{_decimal(contagem.acima_de_dois_esperado)}{alertas}"
        "</tr>"
    )


def _explica_destaques(analise: AnaliseSecoes) -> str:
    return (
        "<p>Até 100 seções de maior |z| por UF em cada cenário. A é o "
        f"{analise.a} e B o {analise.b}. Válidos do 1º turno em A / B / eliminados; votos do "
        "2º turno em A / B. Clique no cabeçalho para ordenar.</p>"
    )


def _destaques(analise: AnaliseSecoes, indice: int) -> str:
    head = _head(
        ("Município", "lugar"),
        ("UF", "num"),
        ("Zona", "num"),
        ("Seção", "num"),
        ("1º turno A / B / eliminados", "num"),
        ("2º turno A / B", "num"),
        ("Esperado A", "num"),
        ("Real A", "num"),
        ("Resíduo", "num"),
        ("Votos de diferença", "num"),
        ("z", "num"),
        ("Grupo", "num"),
        ("Marcas", "num"),
    )
    linhas = "".join(_destaque(secao, indice) for secao in destaques(analise, indice))
    return _bloco(analise, indice, f"{_TABLE_OPEN}{head}<tbody>{linhas}</tbody>{_TABLE_CLOSE}")


def _destaque(secao: SecaoTurnos, indice: int) -> str:
    leitura: Leitura = secao.leituras[indice]
    z = leitura.z or 0.0
    marcas = [_ROTULOS_CLASSE[leitura.classe]] if leitura.classe in _ROTULOS_CLASSE else []
    marcas.extend(_ROTULOS_ALERTA[alerta] for alerta in secao.alertas)
    primeiro = secao.primeiro
    segundo = secao.segundo
    return (
        f'<tr data-uf="{escape(secao.uf)}" data-destaque>'
        f"{_municipio(secao)}{_uf(secao.uf)}{_inteiro(secao.zona)}{_inteiro(secao.secao)}"
        f'<td class="num" data-ord="{primeiro.validos}">'
        f"{primeiro.a} / {primeiro.b} / {primeiro.outros}</td>"
        f'<td class="num" data-ord="{segundo.a + segundo.b}">{segundo.a} / {segundo.b}</td>'
        f"{_fatia(leitura.esperado)}{_fatia(leitura.real)}{_fatia(leitura.residuo)}"
        f"{_inteiro(leitura.votos_de_diferenca)}"
        f'<td class="num" data-ord="{round(z * _SORT_SCALE)}">{_numero(z)}</td>'
        f'<td class="num" data-ord="{_ordem_grupo(secao.grupo)}">'
        f"{escape(_ROTULOS_GRUPO[secao.grupo])}</td>"
        f'<td class="num" data-ord="{len(marcas)}">{escape("; ".join(marcas))}</td>'
        "</tr>"
    )


def _verificacoes(analise: AnaliseSecoes) -> str:
    secoes = com_alerta(analise)
    if not secoes:
        return "<p>Nenhuma seção falhou nas verificações objetivas.</p>"
    head = _head(
        ("Município", "lugar"),
        ("UF", "num"),
        ("Zona", "num"),
        ("Seção", "num"),
        ("Aptos 1º", "num"),
        ("Aptos 2º", "num"),
        ("Complemento 1º / 2º", "num"),
        ("Cédulas 1º", "num"),
        ("Cédulas 2º", "num"),
        ("Variação das cédulas", "num"),
        ("Verificações", "num"),
    )
    linhas = "".join(_verificacao(secao) for secao in secoes)
    return (
        "<p>Estas marcas não dependem de cenário nem do z. O complemento é a contagem de "
        "eleitores que o boletim registra à parte dos aptos.</p>"
        f"{_TABLE_OPEN}{head}<tbody>{linhas}</tbody>{_TABLE_CLOSE}"
    )


def _verificacao(secao: SecaoTurnos) -> str:
    antes = secao.primeiro.cedulas
    depois = secao.segundo.cedulas
    variacao = Fraction(depois - antes, antes) if antes else Fraction(0)
    rotulos = "; ".join(_ROTULOS_ALERTA[alerta] for alerta in ALERTAS if alerta in secao.alertas)
    return (
        f'<tr data-uf="{escape(secao.uf)}">'
        f"{_municipio(secao)}{_uf(secao.uf)}{_inteiro(secao.zona)}{_inteiro(secao.secao)}"
        f"{_inteiro(secao.aptos[0])}{_inteiro(secao.aptos[1])}"
        f'<td class="num" data-ord="{sum(secao.complemento)}">'
        f"{secao.complemento[0]} / {secao.complemento[1]}</td>"
        f"{_inteiro(antes)}{_inteiro(depois)}{_fatia(variacao)}"
        f'<td class="num" data-ord="{len(secao.alertas)}">{escape(rotulos)}</td>'
        "</tr>"
    )


def _faixas(analise: AnaliseSecoes, indice: int) -> str:
    head = _head(
        ("Votos de finalista no 2º turno", "lugar"),
        ("Seções com z", "num"),
        (f"|z| > {_numero(LIMIAR_FORA)}", "num"),
        ("Taxa", "num"),
    )
    linhas = "".join(_faixa(faixa) for faixa in analise.faixas[indice])
    return _bloco(analise, indice, f"{_TABLE_OPEN}{head}<tbody>{linhas}</tbody>{_TABLE_CLOSE}")


def _faixa(faixa: FaixaDeVotos) -> str:
    rotulo = (
        f"{faixa.minimo} ou mais" if faixa.maximo is None else f"{faixa.minimo} a {faixa.maximo}"
    )
    taxa = Fraction(faixa.fora, faixa.secoes) if faixa.secoes else Fraction(0)
    return (
        "<tr>"
        f'<td class="lugar" data-ord="{faixa.minimo:06d}">{escape(rotulo)}</td>'
        f"{_inteiro(faixa.secoes)}{_inteiro(faixa.fora)}{_fatia(taxa)}"
        "</tr>"
    )


def _head(*colunas: tuple[str, str]) -> str:
    celulas = "".join(
        f'<th class="{classe}" scope="col" aria-sort="none">{escape(rotulo)}</th>'
        for rotulo, classe in colunas
    )
    return f"<thead><tr>{celulas}</tr></thead>"


def _municipio(secao: SecaoTurnos) -> str:
    nome = escape(secao.nome)
    return f'<td class="lugar" data-ord="{nome}">{nome}</td>'


def _uf(uf: str) -> str:
    ordem = UF_CODES.index(uf) if uf in UF_CODES else len(UF_CODES)
    return f'<td class="num" data-ord="{ordem}">{escape(uf)}</td>'


def _inteiro(valor: int) -> str:
    return f'<td class="num" data-ord="{valor}">{format_integer(valor)}</td>'


def _decimal(valor: float) -> str:
    return f'<td class="num" data-ord="{round(valor * _SORT_SCALE)}">{_numero(valor)}</td>'


def _fatia(valor: Fraction) -> str:
    ordem = round_half_up(valor * _SORT_SCALE)
    return f'<td class="num" data-ord="{ordem}">{format_percent(valor)}</td>'


def _ordem_grupo(grupo: str) -> int:
    return tuple(_ROTULOS_GRUPO).index(grupo)


def _numero(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",")
