"""Confere a assinatura digital (vota.vsc) de cada seção baixada e grava CSV e HTML."""

import argparse
import csv
import sys
import time
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Final

from eleicoes.adapters.arquivo_atomico import gravar_texto
from eleicoes.domain.assinatura_urna import (
    CADEIA_AC_VENCIDA,
    CADEIA_OK,
    DIVERGE,
    VALIDA,
    ArquivoNoDisco,
    ConferenciaAssinatura,
    conferir_assinaturas,
    sha512,
)
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS
from eleicoes.domain.values import UF_CODES
from eleicoes.use_cases.verificar_urnas import secoes_baixadas

ILEGIVEL: Final = "ilegivel"
SEM_ASSINATURA: Final = "sem_assinatura"
_SUFIXO_BU: Final = "-bu.dat"
_SUFIXO_VSC: Final = "-vota.vsc"
_SUFIXO_LOG: Final = "-log.jez"
_URNA_DIFERE: Final = "urna_difere_do_bu"
# Marcador que o download grava quando o TSE não publica a imagem do BU.
_SUFIXO_AUSENTE: Final = ".ausente"
# O download grava em ".{nome}.partial" e só depois troca pelo nome definitivo.
_PREFIXO_PARCIAL: Final = "."
_ORDEM: Final = (VALIDA, DIVERGE, SEM_ASSINATURA, ILEGIVEL)
_ROTULOS: Final = {
    VALIDA: "Assinatura válida",
    DIVERGE: "Divergem",
    SEM_ASSINATURA: "Sem vota.vsc",
    ILEGIVEL: "Arquivo ilegível",
}


@dataclass(frozen=True, slots=True)
class ResultadoAssinatura:
    uf: str
    caminho: str
    conferencia: ConferenciaAssinatura | None
    erro: str = ""
    situacao_sem_conferencia: str = ILEGIVEL

    @property
    def situacao(self) -> str:
        if self.conferencia is None:
            return self.situacao_sem_conferencia
        return self.conferencia.situacao


Verificar = Callable[[str, str], ResultadoAssinatura]


def verificar_secao(uf: str, caminho: str) -> ResultadoAssinatura:
    """caminho é o BU da seção; o vota.vsc e os outros arquivos estão na mesma pasta."""
    from eleicoes.adapters.asn1.assinatura_reader import autoridades
    from eleicoes.adapters.curvas_urna import verificar_assinatura

    leitores = _leitores()
    prefixo = Path(caminho).name[: -len(_SUFIXO_BU)]
    pasta = Path(caminho).parent
    vsc = pasta / f"{prefixo}{_SUFIXO_VSC}"
    if not vsc.is_file():
        return ResultadoAssinatura(uf, caminho, None, "", SEM_ASSINATURA)
    try:
        pacote = leitores.assinatura.read(vsc.read_bytes())
        no_disco = _no_disco(pasta)
        bu = next(item for item in no_disco if item.nome.endswith(_SUFIXO_BU))
        numero_urna = leitores.bu.read(bu.nome, (pasta / bu.nome).read_bytes()).numero_interno_urna
    except (ElectionError, OSError) as error:
        # OSError: o download em andamento pode trocar um arquivo entre a listagem e a leitura.
        return ResultadoAssinatura(uf, caminho, None, type(error).__name__)
    conferencia = conferir_assinaturas(
        pacote, no_disco, prefixo, numero_urna, autoridades(), verificar_assinatura
    )
    if _URNA_DIFERE in conferencia.divergencias:
        # Só aqui o log é aberto: assinante diferente da urna do BU pede a recuperação de dados.
        try:
            recuperadoras = _recuperadoras(pasta / f"{prefixo}{_SUFIXO_LOG}")
        except (ElectionError, OSError) as error:
            return ResultadoAssinatura(uf, caminho, None, type(error).__name__)
        conferencia = conferir_assinaturas(
            pacote,
            no_disco,
            prefixo,
            numero_urna,
            autoridades(),
            verificar_assinatura,
            recuperadoras,
        )
    return ResultadoAssinatura(uf, caminho, conferencia)


def _recuperadoras(log: Path) -> frozenset[int]:
    from eleicoes.adapters.log_urna import urnas_que_geraram_resultado

    if not log.is_file():
        return frozenset()
    return urnas_que_geraram_resultado(log.read_bytes())


def _no_disco(pasta: Path) -> list[ArquivoNoDisco]:
    found: list[ArquivoNoDisco] = []
    for arquivo in sorted(pasta.iterdir()):
        nome = arquivo.name
        if (
            nome.startswith(_PREFIXO_PARCIAL)
            or nome.endswith((_SUFIXO_VSC, _SUFIXO_AUSENTE))
            or not arquivo.is_file()
        ):
            continue
        conteudo = arquivo.read_bytes()
        found.append(ArquivoNoDisco(nome, len(conteudo), sha512(conteudo)))
    return found


def verificar(
    secoes: Iterable[tuple[str, Path]],
    processos: int,
    verificar_uma: Verificar = verificar_secao,
) -> list[ResultadoAssinatura]:
    pares = [(uf, str(caminho)) for uf, caminho in secoes]
    if processos <= 1:
        return [verificar_uma(uf, caminho) for uf, caminho in pares]
    with ProcessPoolExecutor(max_workers=processos) as executor:
        return list(
            executor.map(
                verificar_uma,
                [uf for uf, _ in pares],
                [caminho for _, caminho in pares],
                chunksize=64,
            )
        )


def resumo_por_uf(resultados: Sequence[ResultadoAssinatura]) -> dict[str, Counter[str]]:
    found: dict[str, Counter[str]] = {}
    for item in resultados:
        contagem = found.setdefault(item.uf, Counter())
        contagem[item.situacao] += 1
        if item.conferencia is not None:
            contagem[f"cadeia:{item.conferencia.cadeia}"] += 1
            contagem[f"algoritmo:{item.conferencia.algoritmo}"] += 1
            if item.conferencia.recuperada:
                contagem["recuperada"] += 1
    return found


def gravar_csv(destino: Path, resultados: Sequence[ResultadoAssinatura]) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(
            [
                "uf",
                "secao",
                "situacao",
                "modelo",
                "algoritmo",
                "urna",
                "emissor",
                "cadeia",
                "conferidos",
                "nao_baixados",
                "divergencias",
                "recuperada",
                "detalhes",
                "arquivo",
            ]
        )
        for item in resultados:
            escritor.writerow(_linha(item))


def html_da_verificacao(ano: int, turno: int, resultados: Sequence[ResultadoAssinatura]) -> str:
    resumo = resumo_por_uf(resultados)
    total: Counter[str] = Counter()
    for contagem in resumo.values():
        total.update(contagem)
    problemas = [item for item in resultados if item.situacao in (DIVERGE, ILEGIVEL)]
    titulo = f"Assinatura digital das urnas — {ano}, {turno}º turno"
    linhas_uf = "".join(_linha_uf(uf, resumo[uf]) for uf in UF_CODES if uf in resumo)
    return (
        '<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{escape(titulo)}</title>\n<style>{_CSS}</style>\n</head>\n<body>\n"
        f"<h1>{escape(titulo)}</h1>\n{_metodo()}\n"
        f'<p class="destaque">{_frase(total)}</p>\n'
        "<h2>Por UF</h2>\n<table><thead><tr><th>UF</th><th>Seções</th>"
        + "".join(f"<th>{_ROTULOS[chave]}</th>" for chave in _ORDEM)
        + "<th>Cadeia até a AC</th><th>AC vencida na data</th><th>Ed521</th><th>ECDSA</th>"
        + "<th>Assinada pela urna de recuperação</th>"
        + "</tr></thead><tbody>"
        + linhas_uf
        + _linha_uf("Total", total)
        + "</tbody></table>\n"
        + _tabela_de_problemas(problemas)
        + "</body>\n</html>\n"
    )


def main(argv: Sequence[str] | None = None, verificar_uma: Verificar = verificar_secao) -> int:
    args = _parser().parse_args(argv)
    raiz = Path(args.origem) / str(args.ano) / "arquivo-urna" / f"turno-{args.turno}"
    if not raiz.is_dir():
        print(f"Não há urnas baixadas em {raiz}.", file=sys.stderr)
        return EXIT_FAILURE
    ufs = [uf.upper() for uf in args.uf] or [p.name for p in sorted(raiz.iterdir()) if p.is_dir()]
    inicio = time.monotonic()
    resultados = verificar(secoes_baixadas(raiz, ufs), int(args.processos), verificar_uma)
    duracao = time.monotonic() - inicio
    destino = Path(args.destino or f"relatorios/assinaturas-urnas-{args.ano}-turno-{args.turno}")
    gravar_csv(destino.with_suffix(".csv"), resultados)
    html = html_da_verificacao(int(args.ano), int(args.turno), resultados)
    gravar_texto(destino.with_suffix(".html"), html)
    _imprimir(destino, resultados, duracao)
    return EXIT_SUCCESS


class _Leitores:
    def __init__(self) -> None:
        from eleicoes.adapters.asn1.assinatura_reader import Asn1AssinaturaReader
        from eleicoes.adapters.asn1.boletim_reader import Asn1BoletimReader

        self.assinatura = Asn1AssinaturaReader()
        self.bu = Asn1BoletimReader()


_CACHE: list[_Leitores] = []


def _leitores() -> _Leitores:
    """Compilar as especificações custa caro: cada processo compila uma vez."""
    if not _CACHE:
        _CACHE.append(_Leitores())
    return _CACHE[0]


def _linha(item: ResultadoAssinatura) -> list[object]:
    secao = Path(item.caminho).name[: -len(_SUFIXO_BU)]
    conferencia = item.conferencia
    if conferencia is None:
        return [
            item.uf,
            secao,
            item.situacao,
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            item.erro,
            "",
            "",
            item.caminho,
        ]
    detalhes = "; ".join(f"{chave}: {texto}" for chave, texto in conferencia.detalhes.items())
    return [
        item.uf,
        secao,
        conferencia.situacao,
        conferencia.modelo,
        conferencia.algoritmo,
        conferencia.urna,
        conferencia.emissor,
        conferencia.cadeia,
        "|".join(nome.split("-", 1)[-1] for nome in conferencia.conferidos),
        conferencia.nao_baixados,
        "|".join(conferencia.divergencias),
        "sim" if conferencia.recuperada else "",
        detalhes,
        item.caminho,
    ]


def _linha_uf(uf: str, contagem: Counter[str]) -> str:
    secoes = sum(contagem[chave] for chave in _ORDEM)
    celulas = "".join(f"<td>{_milhar(contagem[chave])}</td>" for chave in _ORDEM)
    extras = (
        f"cadeia:{CADEIA_OK}",
        f"cadeia:{CADEIA_AC_VENCIDA}",
        "algoritmo:ed521",
        "algoritmo:ecdsa_p521",
        "recuperada",
    )
    return (
        f"<tr><th>{escape(uf)}</th><td>{_milhar(secoes)}</td>{celulas}"
        + "".join(f"<td>{_milhar(contagem[chave])}</td>" for chave in extras)
        + "</tr>"
    )


def _tabela_de_problemas(problemas: Sequence[ResultadoAssinatura]) -> str:
    if not problemas:
        return "<h2>Seções com assinatura que não confere</h2>\n<p>Nenhuma.</p>\n"
    linhas = "".join(
        "<tr>" + "".join(f"<td>{escape(str(valor))}</td>" for valor in _linha(item)[:13]) + "</tr>"
        for item in problemas
    )
    return (
        "<h2>Seções com assinatura que não confere</h2>\n<table><thead><tr><th>UF</th>"
        "<th>Seção</th><th>Situação</th><th>Modelo</th><th>Algoritmo</th><th>Urna</th>"
        "<th>Emissor</th><th>Cadeia</th><th>Conferidos</th><th>Não baixados</th>"
        "<th>Divergências</th><th>Recuperada</th><th>Detalhes</th></tr></thead>"
        f"<tbody>{linhas}</tbody></table>\n"
    )


def _frase(total: Counter[str]) -> str:
    secoes = sum(total[chave] for chave in _ORDEM)
    return (
        f"{_milhar(secoes)} seções conferidas: {_milhar(total[VALIDA])} com hashes e assinatura "
        f"válidos, {_milhar(total[DIVERGE])} com divergência, {_milhar(total[SEM_ASSINATURA])} "
        f"sem o vota.vsc e {_milhar(total[ILEGIVEL])} com arquivo ilegível."
    )


def _metodo() -> str:
    return (
        "<p>Para cada seção baixada, o arquivo de assinaturas da urna (vota.vsc) é decodificado "
        "com a especificação publicada pelo TSE, ajustada ao formato de 2026. O SHA-512 e o "
        "tamanho de cada arquivo baixado (BU, RDV, log e, quando há, a imagem do BU) precisam "
        "bater com a lista da urna; as listas de software e de hardware precisam ser iguais; a "
        "lista e cada arquivo baixado precisam ter assinatura de hardware válida (Ed521 nas "
        "urnas UE2020 e UE2022, ECDSA P-521 nas anteriores) sob a chave do certificado que "
        "vai no próprio arquivo; o certificado precisa ser da urna do BU, estar na validade e "
        "ter sido assinado por uma das ACs do TSE que emitem certificados de urna (AC URNA, "
        "AC UE2020, AC UE2022), cujos certificados vêm do script de verificação publicado "
        "pelo TSE. Não são verificados: a assinatura dessas ACs pelas raízes AC RAIZ UE e "
        "AC URNA v2, cujos certificados não são públicos; a revogação dos certificados; e a "
        "assinatura de software (CEPESC), de algoritmo proprietário. A AC URNA, que emite os "
        "certificados das urnas UE2009 a UE2015, venceu em 18/07/2026, antes da eleição: essas "
        "seções aparecem como “AC vencida na data”, com assinatura e cadeia de resto válidas. "
        "Quando a mídia de resultado falha, outra urna roda o Recuperador de Dados, regrava os "
        "arquivos e os assina com o próprio certificado; o assinante só é aceito diferente da "
        "urna do BU se o log do pacote mostrar essa urna gerando os arquivos de resultado. "
        "Arquivos listados pela urna e não publicados pelo TSE (foto do BU da zona, "
        "biometria e outros) entram só pela assinatura da lista.</p>"
    )


def _imprimir(destino: Path, resultados: Sequence[ResultadoAssinatura], duracao: float) -> None:
    total: Counter[str] = Counter(item.situacao for item in resultados)
    cadeias: Counter[str] = Counter(
        item.conferencia.cadeia for item in resultados if item.conferencia is not None
    )
    print(f"Verificação gravada em {destino.with_suffix('.html')} e {destino.with_suffix('.csv')}.")
    print(", ".join(f"{_ROTULOS[chave]}: {_milhar(total[chave])}" for chave in _ORDEM) + ".")
    print("Cadeia: " + ", ".join(f"{chave} {_milhar(n)}" for chave, n in sorted(cadeias.items())))
    por_secao = duracao / len(resultados) if resultados else 0.0
    print(f"{duracao:.0f} s, {1000 * por_secao:.1f} ms por seção.")


def _milhar(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Confere a assinatura digital das urnas baixadas.")
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--turno", type=int, choices=(1, 2), default=2)
    parser.add_argument("--uf", action="append", default=[], help="Sigla. Pode repetir.")
    parser.add_argument("--origem", default="downloads", help="Pasta dos downloads.")
    parser.add_argument("--processos", type=int, default=2)
    parser.add_argument("--destino", help="Caminho sem extensão do CSV e do HTML.")
    return parser


_CSS: Final = (
    "body{font:14px/1.5 system-ui,sans-serif;margin:1.5rem;color:#111;background:#fff}"
    "h1{font-size:1.6rem}table{border-collapse:collapse;margin:.5rem 0 1.5rem}"
    "th,td{border:1px solid #ccc;padding:.25rem .5rem;text-align:right}"
    "th:first-child,td:last-child{text-align:left}thead th{background:#f2f2f2}"
    ".destaque{font-size:1.1rem;font-weight:600}"
    "@media (prefers-color-scheme:dark){body{background:#111;color:#eee}"
    "th,td{border-color:#444}thead th{background:#222}}"
)
