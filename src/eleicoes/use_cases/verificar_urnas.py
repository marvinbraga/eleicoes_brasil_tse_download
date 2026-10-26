"""Confere BU × RDV × log de cada seção baixada e grava CSV e HTML com o resultado."""

import argparse
import csv
import sys
from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Final

from eleicoes.adapters.arquivo_atomico import gravar_texto
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.integridade_urna import (
    CONFERE,
    DIVERGE,
    SEM_LOG,
    SEM_RDV,
    Conferencia,
    conferir,
)
from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS
from eleicoes.domain.values import UF_CODES

ILEGIVEL: Final = "ilegivel"
_SUFIXO_BU: Final = "-bu.dat"
_ORDEM: Final = (CONFERE, DIVERGE, SEM_RDV, SEM_LOG, ILEGIVEL)
_ROTULOS: Final = {
    CONFERE: "Conferem",
    DIVERGE: "Divergem",
    SEM_RDV: "Sem RDV",
    SEM_LOG: "Sem log",
    ILEGIVEL: "Arquivo ilegível",
}


@dataclass(frozen=True, slots=True)
class ResultadoSecao:
    uf: str
    caminho: str
    conferencia: Conferencia | None
    erro: str = ""

    @property
    def situacao(self) -> str:
        return ILEGIVEL if self.conferencia is None else self.conferencia.situacao


Verificar = Callable[[str, str], ResultadoSecao]


def secoes_baixadas(raiz: Path, ufs: Sequence[str]) -> Iterator[tuple[str, Path]]:
    for uf in ufs:
        for bu in sorted((raiz / uf).glob(f"*/*/*/*{_SUFIXO_BU}")):
            yield uf, bu


def verificar_secao(uf: str, caminho: str) -> ResultadoSecao:
    """Lê os três arquivos de uma seção. Arquivo ausente vira None; ilegível vira erro."""
    from eleicoes.adapters.log_urna import dia_do_boletim, resumo_do_log

    leitores = _leitores()
    base = caminho[: -len(_SUFIXO_BU)]
    try:
        boletim = leitores.bu.read(Path(caminho).name, Path(caminho).read_bytes())
        rdv_bytes = _bytes(f"{base}-rdv.dat")
        log_bytes = _bytes(f"{base}-log.jez")
        rdv = None if rdv_bytes is None else leitores.rdv.read(rdv_bytes)
        dia = dia_do_boletim(boletim.data_hora_emissao)
        log = None if log_bytes is None else resumo_do_log(log_bytes, dia)
    except ElectionError as error:
        return ResultadoSecao(uf, caminho, None, type(error).__name__)
    return ResultadoSecao(uf, caminho, conferir(boletim, rdv, log))


def verificar(
    secoes: Iterable[tuple[str, Path]],
    processos: int,
    verificar_uma: Verificar = verificar_secao,
) -> list[ResultadoSecao]:
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


def resumo_por_uf(resultados: Sequence[ResultadoSecao]) -> dict[str, Counter[str]]:
    found: dict[str, Counter[str]] = {}
    for item in resultados:
        contagem = found.setdefault(item.uf, Counter())
        contagem[item.situacao] += 1
        if item.conferencia is not None and item.conferencia.urna_trocada:
            contagem["urna_trocada"] += 1
    return found


def gravar_csv(destino: Path, resultados: Sequence[ResultadoSecao]) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(
            [
                "uf",
                "municipio",
                "zona",
                "secao",
                "urna",
                "situacao",
                "urna_trocada",
                "divergencias",
                "detalhes",
                "arquivo",
            ]
        )
        for item in resultados:
            escritor.writerow(_linha(item))


def html_da_verificacao(ano: int, turno: int, resultados: Sequence[ResultadoSecao]) -> str:
    resumo = resumo_por_uf(resultados)
    total: Counter[str] = Counter()
    for contagem in resumo.values():
        total.update(contagem)
    problemas = [item for item in resultados if item.situacao in (DIVERGE, ILEGIVEL)]
    titulo = f"Integridade das urnas — {ano}, {turno}º turno"
    linhas_uf = "".join(_linha_uf(uf, resumo[uf]) for uf in UF_CODES if uf in resumo)
    return (
        '<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{escape(titulo)}</title>\n<style>{_CSS}</style>\n</head>\n<body>\n"
        f"<h1>{escape(titulo)}</h1>\n{_metodo()}\n"
        f'<p class="destaque">{_frase(total)}</p>\n'
        "<h2>Por UF</h2>\n<table><thead><tr><th>UF</th><th>Seções</th>"
        + "".join(f"<th>{_ROTULOS[chave]}</th>" for chave in _ORDEM)
        + "<th>Urna trocada</th></tr></thead><tbody>"
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
    resultados = verificar(secoes_baixadas(raiz, ufs), int(args.processos), verificar_uma)
    destino = Path(args.destino or f"relatorios/integridade-urnas-{args.ano}-turno-{args.turno}")
    gravar_csv(destino.with_suffix(".csv"), resultados)
    html = html_da_verificacao(int(args.ano), int(args.turno), resultados)
    gravar_texto(destino.with_suffix(".html"), html)
    _imprimir(destino, resultados)
    return EXIT_SUCCESS


class _Leitores:
    def __init__(self) -> None:
        from eleicoes.adapters.asn1.boletim_reader import Asn1BoletimReader
        from eleicoes.adapters.asn1.rdv_reader import Asn1RdvReader

        self.bu = Asn1BoletimReader()
        self.rdv = Asn1RdvReader()


_CACHE: list[_Leitores] = []


def _leitores() -> _Leitores:
    """Compilar as especificações custa caro: cada processo compila uma vez."""
    if not _CACHE:
        _CACHE.append(_Leitores())
    return _CACHE[0]


def _bytes(caminho: str) -> bytes | None:
    try:
        return Path(caminho).read_bytes()
    except FileNotFoundError:
        return None


def _linha(item: ResultadoSecao) -> list[object]:
    conferencia = item.conferencia
    if conferencia is None:
        return [item.uf, "", "", "", "", ILEGIVEL, "", item.erro, "", item.caminho]
    detalhes = "; ".join(f"{chave}: {texto}" for chave, texto in conferencia.detalhes.items())
    return [
        item.uf,
        conferencia.municipio,
        conferencia.zona,
        conferencia.secao,
        conferencia.numero_interno_urna,
        conferencia.situacao,
        "sim" if conferencia.urna_trocada else "",
        "|".join(conferencia.divergencias),
        detalhes,
        item.caminho,
    ]


def _linha_uf(uf: str, contagem: Counter[str]) -> str:
    secoes = sum(contagem[chave] for chave in _ORDEM)
    celulas = "".join(f"<td>{_milhar(contagem[chave])}</td>" for chave in _ORDEM)
    return (
        f"<tr><th>{escape(uf)}</th><td>{_milhar(secoes)}</td>{celulas}"
        f"<td>{_milhar(contagem['urna_trocada'])}</td></tr>"
    )


def _tabela_de_problemas(problemas: Sequence[ResultadoSecao]) -> str:
    if not problemas:
        return "<h2>Seções que não conferem</h2>\n<p>Nenhuma.</p>\n"
    linhas = "".join(
        "<tr>" + "".join(f"<td>{escape(str(valor))}</td>" for valor in _linha(item)[:9]) + "</tr>"
        for item in problemas
    )
    return (
        "<h2>Seções que não conferem</h2>\n<table><thead><tr><th>UF</th><th>Município</th>"
        "<th>Zona</th><th>Seção</th><th>Urna</th><th>Situação</th><th>Urna trocada</th>"
        f"<th>Divergências</th><th>Detalhes</th></tr></thead><tbody>{linhas}</tbody></table>\n"
    )


def _frase(total: Counter[str]) -> str:
    secoes = sum(total[chave] for chave in _ORDEM)
    return (
        f"{_milhar(secoes)} seções conferidas: {_milhar(total[CONFERE])} com BU, RDV e log "
        f"fechando entre si, {_milhar(total[DIVERGE])} com divergência, "
        f"{_milhar(total[SEM_RDV] + total[SEM_LOG])} sem algum dos arquivos e "
        f"{_milhar(total[ILEGIVEL])} com arquivo ilegível."
    )


def _metodo() -> str:
    return (
        "<p>Para cada seção baixada, o RDV (cada voto gravado, um a um) é recontado cargo a "
        "cargo e comparado com o boletim de urna (BU). O log da urna, no dia da votação, "
        "precisa registrar um voto computado por eleitor do BU e um voto de presidente e de "
        "governador por eleitor desses cargos, contando os nulos atribuídos por suspensão. "
        "BU, RDV e log precisam apontar a mesma seção e a mesma urna. Urna trocada durante "
        "a votação é procedimento previsto e aparece à parte. A assinatura digital dos "
        "arquivos não é verificada aqui.</p>"
    )


def _imprimir(destino: Path, resultados: Sequence[ResultadoSecao]) -> None:
    total: Counter[str] = Counter(item.situacao for item in resultados)
    print(f"Verificação gravada em {destino.with_suffix('.html')} e {destino.with_suffix('.csv')}.")
    print(", ".join(f"{_ROTULOS[chave]}: {_milhar(total[chave])}" for chave in _ORDEM) + ".")


def _milhar(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Confere BU × RDV × log das urnas baixadas.")
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--turno", type=int, choices=(1, 2), default=2)
    parser.add_argument("--uf", action="append", default=[], help="Sigla. Pode repetir.")
    parser.add_argument("--origem", default="downloads", help="Pasta dos downloads.")
    parser.add_argument("--processos", type=int, default=4)
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
