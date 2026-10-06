"""Findings over boletim projections. Rules run here, not in the adapter."""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from eleicoes.domain.boletim_consulta import (
    BlankNullProjection,
    IndicioBoletim,
    NominalProjection,
    SectionProjection,
)
from eleicoes.domain.correspondencia.indicio import MODIFIED_Z_THRESHOLD, Gravidade
from eleicoes.domain.correspondencia.statistics import median, median_absolute_deviation, modified_z
from eleicoes.domain.errors import InvalidBoletimConsultaError

MIN_COMPARECIMENTO: Final = 10
_SENADOR: Final = "senador"
_SENADOR_SEATS: Final = 2
_GRAVITY_ORDER: Final = {
    Gravidade.ALTA: 0,
    Gravidade.MEDIA: 1,
    Gravidade.BAIXA: 2,
}


@dataclass(frozen=True, slots=True)
class _Leader:
    numero: int
    quantidade: int


@dataclass(frozen=True, slots=True)
class _Rate:
    municipio: int
    rate: float
    numero: int | None = None


def evaluate_findings(
    uf: str,
    cargo: str,
    sections: Iterable[SectionProjection],
    nominal_votes: Iterable[NominalProjection],
    blank_votes: Iterable[BlankNullProjection],
) -> tuple[IndicioBoletim, ...]:
    listed = tuple(sections)
    attendance = _attendance(listed)
    found = (
        *_sum_divergences(uf, cargo, listed),
        *_concentration(uf, attendance, nominal_votes),
        *_blank_null(uf, attendance, blank_votes),
    )
    return tuple(sorted(found, key=_finding_order))


def _attendance(sections: Sequence[SectionProjection]) -> dict[int, int]:
    totals: dict[int, int] = {}
    for section in sections:
        totals[section.municipio] = totals.get(section.municipio, 0) + section.comparecimento
    return totals


def _sum_divergences(
    uf: str,
    cargo: str,
    sections: Sequence[SectionProjection],
) -> tuple[IndicioBoletim, ...]:
    return tuple(
        _divergence(uf, section, _expected(cargo, section.comparecimento))
        for section in sections
        if section.quantidade != _expected(cargo, section.comparecimento)
    )


def _expected(cargo: str, comparecimento: int) -> int:
    if cargo == _SENADOR:
        return comparecimento * _SENADOR_SEATS
    return comparecimento


def _divergence(uf: str, section: SectionProjection, expected: int) -> IndicioBoletim:
    return IndicioBoletim(
        codigo="soma_diverge",
        descricao=(
            f"A soma dos votos da seção {section.secao}, zona {section.zona}, "
            f"município {section.municipio}, diverge do comparecimento do cargo."
        ),
        gravidade=Gravidade.ALTA,
        uf=uf,
        municipio=section.municipio,
        zona=section.zona,
        secao=section.secao,
        medida=f"sum {section.quantidade}; expected {expected}",
    )


def _concentration(
    uf: str,
    attendance: Mapping[int, int],
    nominal_votes: Iterable[NominalProjection],
) -> tuple[IndicioBoletim, ...]:
    leaders = _leaders(nominal_votes)
    rates = _leader_rates(attendance, leaders)
    return tuple(_concentration_finding(uf, item, score) for item, score in _scored(rates))


def _blank_null(
    uf: str,
    attendance: Mapping[int, int],
    blank_votes: Iterable[BlankNullProjection],
) -> tuple[IndicioBoletim, ...]:
    blanks = _blank_totals(blank_votes)
    rates = _blank_rates(attendance, blanks)
    return tuple(_blank_finding(uf, item, score) for item, score in _scored(rates))


def _leader_rates(
    attendance: Mapping[int, int],
    leaders: Mapping[int, _Leader],
) -> tuple[_Rate, ...]:
    rates: list[_Rate] = []
    for municipio, comparecimento in attendance.items():
        leader = leaders.get(municipio)
        if comparecimento < MIN_COMPARECIMENTO or leader is None:
            continue
        rates.append(_Rate(municipio, leader.quantidade / comparecimento, leader.numero))
    return tuple(rates)


def _blank_rates(attendance: Mapping[int, int], blanks: Mapping[int, int]) -> tuple[_Rate, ...]:
    return tuple(
        _Rate(municipio, blanks.get(municipio, 0) / comparecimento)
        for municipio, comparecimento in attendance.items()
        if comparecimento >= MIN_COMPARECIMENTO
    )


def _leaders(rows: Iterable[NominalProjection]) -> dict[int, _Leader]:
    totals: dict[tuple[int, int], int] = {}
    for row in rows:
        key = (row.municipio, row.numero)
        totals[key] = totals.get(key, 0) + row.quantidade
    best: dict[int, _Leader] = {}
    for (municipio, numero), quantidade in totals.items():
        candidate = _Leader(numero, quantidade)
        current = best.get(municipio)
        if _prefer_leader(candidate, current):
            best[municipio] = candidate
    return best


def _prefer_leader(candidate: _Leader, current: _Leader | None) -> bool:
    if current is None:
        return True
    if candidate.quantidade != current.quantidade:
        return candidate.quantidade > current.quantidade
    return candidate.numero < current.numero


def _blank_totals(rows: Iterable[BlankNullProjection]) -> dict[int, int]:
    totals: dict[int, int] = {}
    for row in rows:
        totals[row.municipio] = totals.get(row.municipio, 0) + row.quantidade
    return totals


def _scored(rates: Sequence[_Rate]) -> tuple[tuple[_Rate, float], ...]:
    if len(rates) < 2:
        return ()
    values = [item.rate for item in rates]
    center = median(values)
    spread = median_absolute_deviation(values, center)
    # A zero MAD would make the modified z infinite off the median.
    if spread == 0:
        return ()
    found: list[tuple[_Rate, float]] = []
    for item in rates:
        score = modified_z(item.rate, center, spread)
        if score >= MODIFIED_Z_THRESHOLD:
            found.append((item, score))
    return tuple(found)


def _concentration_finding(uf: str, item: _Rate, score: float) -> IndicioBoletim:
    numero = _required_numero(item.numero)
    return IndicioBoletim(
        codigo="concentracao",
        descricao=(
            f"O município {item.municipio} concentra os votos nominais no número {numero} "
            "fora do padrão dos demais municípios."
        ),
        gravidade=Gravidade.MEDIA,
        uf=uf,
        municipio=item.municipio,
        zona=None,
        secao=None,
        medida=f"number {numero}; share {item.rate:.4f}; z {score:.1f}",
    )


def _blank_finding(uf: str, item: _Rate, score: float) -> IndicioBoletim:
    return IndicioBoletim(
        codigo="brancos_nulos",
        descricao=(
            f"O município {item.municipio} tem proporção de votos brancos e nulos "
            "fora do padrão dos demais municípios."
        ),
        gravidade=Gravidade.MEDIA,
        uf=uf,
        municipio=item.municipio,
        zona=None,
        secao=None,
        medida=f"share {item.rate:.4f}; z {score:.1f}",
    )


def _required_numero(numero: int | None) -> int:
    if numero is None:
        raise InvalidBoletimConsultaError("numero")
    return numero


def _finding_order(item: IndicioBoletim) -> tuple[int, int, int, int, str]:
    zona = -1 if item.zona is None else item.zona
    secao = -1 if item.secao is None else item.secao
    return (_GRAVITY_ORDER[item.gravidade], item.municipio, zona, secao, item.codigo)
