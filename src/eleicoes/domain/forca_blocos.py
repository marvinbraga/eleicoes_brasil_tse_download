"""Optional blocks joined to the strength scoreboard: seat estimates (plano 2) and 2024
municipal counts (plano 6). Pure functions over the scoreboard values; counts stay integers.
"""

from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime

from eleicoes.domain.forca import (
    FEDERACAO,
    MUNICIPAL_2024_VAZIO,
    PAIS,
    PARTIDO,
    PREFIXO_FEDERACAO,
    BaseCadeiras,
    BaseMunicipal2024,
    BlocoCadeiras,
    BlocoMunicipal2024,
    Cadeiras,
    FederacaoForca,
    ForcaUnidade,
    Municipal2024Forca,
    PlacarForca,
    Recorte,
    chave_federacao,
    ordem_unidade,
)

LinhasCadeiras = Mapping[tuple[str, str], Cadeiras]


def com_cadeiras(placar: PlacarForca, linhas: LinhasCadeiras, totais: BaseCadeiras) -> PlacarForca:
    """Joins the seat rows by (chave, uf); the country uses the simulation totals."""
    return replace(
        placar,
        pais=_recorte_com_cadeiras(placar.pais, linhas, totais),
        ufs=tuple(
            _recorte_com_cadeiras(uf, linhas, _base_cadeiras_uf(linhas, uf.codigo))
            for uf in placar.ufs
        ),
        cadeiras=BlocoCadeiras(disponivel=True, totais=totais),
    )


def sem_cadeiras(placar: PlacarForca) -> PlacarForca:
    return replace(placar, cadeiras=BlocoCadeiras(disponivel=False, totais=None))


def _recorte_com_cadeiras(
    recorte: Recorte,
    linhas: LinhasCadeiras,
    base: BaseCadeiras | None,
) -> Recorte:
    if base is None:
        return recorte

    def juntar(unidades: tuple[ForcaUnidade, ...]) -> tuple[ForcaUnidade, ...]:
        return tuple(
            replace(unidade, cadeiras=linhas.get((unidade.chave, recorte.codigo)))
            for unidade in unidades
        )

    federada = recorte.base_federada
    return replace(
        recorte,
        base=replace(recorte.base, cadeiras=base),
        unidades=juntar(recorte.unidades),
        federadas=juntar(recorte.federadas),
        base_federada=None if federada is None else replace(federada, cadeiras=base),
    )


def _base_cadeiras_uf(linhas: LinhasCadeiras, uf: str) -> BaseCadeiras | None:
    """Party rows only; one governorship when the UF has a winner or two finalists."""
    daqui = [
        valor
        for (chave, lugar), valor in linhas.items()
        if lugar == uf and not chave.startswith(PREFIXO_FEDERACAO)
    ]
    if not daqui:
        return None
    eleitos = sum((valor.governador_1t or 0) + (valor.governador_2t or 0) for valor in daqui)
    return BaseCadeiras(
        camara=sum(valor.camara or 0 for valor in daqui),
        senado=sum(valor.senado or 0 for valor in daqui),
        governadores=min(1, eleitos),
        assembleias=sum(valor.assembleia or 0 for valor in daqui),
    )


Linhas2024 = Mapping[tuple[int, str], Municipal2024Forca]


def com_municipal_2024(
    placar: PlacarForca,
    linhas: Linhas2024,
    totais: Mapping[str, BaseMunicipal2024],
    data_corte: datetime,
    *,
    federacoes: tuple[FederacaoForca, ...],
) -> PlacarForca:
    """Joins 2024 counts by (partido, uf). A federation adds its declared members: these
    counts are additive, unlike leaderships (F18). A cut without totals (DF, abroad) stays
    blank. Parties with 2024 counts but no 2026 vote in a cut get their own row; in the
    joined view, members of a federation absent from the cut form its row.
    """
    juntar = _Juntar2024(linhas, federacoes)
    return replace(
        placar,
        pais=juntar.recorte(placar.pais, totais.get(PAIS)),
        ufs=tuple(juntar.recorte(uf, totais.get(uf.codigo)) for uf in placar.ufs),
        municipal_2024=BlocoMunicipal2024(True, data_corte, totais.get(PAIS)),
    )


def sem_municipal_2024(placar: PlacarForca) -> PlacarForca:
    return replace(placar, municipal_2024=BlocoMunicipal2024(False, None, None))


class _Juntar2024:
    def __init__(self, linhas: Linhas2024, federacoes: tuple[FederacaoForca, ...]) -> None:
        self._linhas = linhas
        self._federacoes = federacoes

    def recorte(self, recorte: Recorte, base: BaseMunicipal2024 | None) -> Recorte:
        if base is None:
            return recorte
        federada = recorte.base_federada
        return replace(
            recorte,
            base=replace(recorte.base, municipal_2024=base),
            unidades=self._unidades(recorte.unidades, recorte.codigo, ()),
            # No federations, no joined view: rows from 2024 must not create one.
            federadas=self._unidades(recorte.federadas, recorte.codigo, self._federacoes)
            if recorte.federadas
            else (),
            base_federada=None if federada is None else replace(federada, municipal_2024=base),
        )

    def _unidades(
        self,
        unidades: tuple[ForcaUnidade, ...],
        uf: str,
        federacoes: tuple[FederacaoForca, ...],
    ) -> tuple[ForcaUnidade, ...]:
        com = tuple(
            replace(unidade, municipal_2024=_soma_2024(self._linhas, unidade.partidos, uf))
            for unidade in unidades
        )
        cobertos = {partido for unidade in unidades for partido in unidade.partidos}
        novas = (
            *self._federacoes_ausentes(uf, cobertos, federacoes),
            *_so_2024(self._linhas, uf, cobertos | _membros_de(federacoes)),
        )
        return tuple(sorted((*com, *novas), key=ordem_unidade))

    def _federacoes_ausentes(
        self,
        uf: str,
        cobertos: set[int],
        federacoes: tuple[FederacaoForca, ...],
    ) -> tuple[ForcaUnidade, ...]:
        ausentes = (item for item in federacoes if not cobertos & set(item.partidos))
        com_contagem = ((item, _soma_2024(self._linhas, item.partidos, uf)) for item in ausentes)
        return tuple(
            _unidade_so_2024(chave_federacao(item.codigo), item.partidos, valor, item.nome)
            for item, valor in com_contagem
            if valor != MUNICIPAL_2024_VAZIO
        )


def _membros_de(federacoes: tuple[FederacaoForca, ...]) -> set[int]:
    return {partido for item in federacoes for partido in item.partidos}


def _so_2024(linhas: Linhas2024, uf: str, cobertos: set[int]) -> tuple[ForcaUnidade, ...]:
    """Parties with 2024 counts in the cut but no 2026 vote there: their own row, votes blank."""
    return tuple(
        _unidade_so_2024(str(partido), (partido,), valor)
        for (partido, lugar), valor in linhas.items()
        if lugar == uf and partido not in cobertos and valor != MUNICIPAL_2024_VAZIO
    )


def _unidade_so_2024(
    chave: str,
    partidos: tuple[int, ...],
    valor: Municipal2024Forca,
    nome: str | None = None,
) -> ForcaUnidade:
    return ForcaUnidade(
        chave=chave,
        partidos=tuple(sorted(partidos)),
        presidente=None,
        deputado_federal=None,
        deputado_estadual=None,
        ufs_lider_estadual=None,
        municipal=None,
        tipo=PARTIDO if nome is None else FEDERACAO,
        nome=nome,
        municipal_2024=valor,
    )


def _soma_2024(linhas: Linhas2024, partidos: tuple[int, ...], uf: str) -> Municipal2024Forca:
    """A party without a row elected nobody there: 0, not blank (F8)."""
    achados = [linhas.get((partido, uf), MUNICIPAL_2024_VAZIO) for partido in partidos]
    return Municipal2024Forca(
        prefeitos=sum(item.prefeitos for item in achados),
        eleitorado_governado=sum(item.eleitorado_governado for item in achados),
        vereadores=sum(item.vereadores for item in achados),
    )
