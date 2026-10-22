"""Proportional seats: Código Eleitoral arts. 106-109 after ADIs 7228, 7263 and 7325.

1. Quociente partidário, only for candidates with at least 10% of the quociente eleitoral.
2. Highest averages among lists with at least 80% of the quotient whose best remaining
   candidate has at least 20% of it (art. 109, I-II and § 2).
3. Highest averages among every list, without thresholds (art. 109, III, as the STF read it).

Average = list votes / (quociente partidário + seats won by average + 1), as in
Res.-TSE 23.677/2021, art. 11, §§ 1 and 5. Ties: more list votes, then more votes for the
next candidate (art. 11, §§ 6-7), then the smaller list code. The data has no candidate
age (art. 110), so a tie between candidates goes to the smaller number and is flagged.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Final

from eleicoes.domain.errors import InvalidSeatRuleError

FASE_QUOCIENTE: Final = "quociente"
FASE_MEDIA: Final = "media"
FASE_MEDIA_LIVRE: Final = "media_livre"


@dataclass(frozen=True, slots=True)
class Candidato:
    """`partido` is the candidate's own party, which differs from the list in a federation."""

    numero: int
    partido: int
    votos: int

    def __post_init__(self) -> None:
        _require_count(self.numero, "numero")
        _require_count(self.partido, "partido")
        _require_count(self.votos, "votos")


@dataclass(frozen=True, slots=True)
class Lista:
    """One party alone or one federation. Candidates of a federation keep their own number."""

    legenda: str
    votos_legenda: int
    candidatos: tuple[Candidato, ...]

    def __post_init__(self) -> None:
        if not self.legenda.strip():
            raise InvalidSeatRuleError("legenda")
        _require_count(self.votos_legenda, "votos_legenda")
        numbers = [candidato.numero for candidato in self.candidatos]
        if len(numbers) != len(set(numbers)):
            raise InvalidSeatRuleError("numero")
        ordered = tuple(sorted(self.candidatos, key=lambda c: (-c.votos, c.numero)))
        object.__setattr__(self, "candidatos", ordered)

    @property
    def votos(self) -> int:
        return self.votos_legenda + sum(candidato.votos for candidato in self.candidatos)


@dataclass(frozen=True, slots=True)
class Eleito:
    legenda: str
    numero: int
    partido: int
    votos: int
    fase: str
    empate: bool


@dataclass(frozen=True, slots=True)
class ResultadoLista:
    legenda: str
    votos: int
    votos_legenda: int
    quociente_partidario: int
    cadeiras_quociente: int
    cadeiras_media: int
    cadeiras_media_livre: int

    @property
    def cadeiras(self) -> int:
        return self.cadeiras_quociente + self.cadeiras_media + self.cadeiras_media_livre


@dataclass(frozen=True, slots=True)
class ResultadoProporcional:
    vagas: int
    votos_validos: int
    quociente_eleitoral: int
    listas: tuple[ResultadoLista, ...]
    eleitos: tuple[Eleito, ...]

    @property
    def vagas_sem_candidato(self) -> int:
        return self.vagas - len(self.eleitos)


def quociente_eleitoral(votos_validos: int, vagas: int) -> int:
    """Art. 106: a fraction of one half or less is dropped; more than one half rounds up."""
    _require_count(votos_validos, "votos_validos")
    if isinstance(vagas, bool) or not isinstance(vagas, int) or vagas < 1:
        raise InvalidSeatRuleError("vagas")
    quotient, remainder = divmod(votos_validos, vagas)
    return quotient + 1 if 2 * remainder > vagas else quotient


def distribuir(vagas: int, listas: Sequence[Lista]) -> ResultadoProporcional:
    codes = [lista.legenda for lista in listas]
    if len(codes) != len(set(codes)):
        raise InvalidSeatRuleError("legenda")
    validos = sum(lista.votos for lista in listas)
    qe = quociente_eleitoral(validos, vagas)
    ordered = tuple(sorted(listas, key=lambda lista: lista.legenda))
    if qe == 0:
        return ResultadoProporcional(vagas, validos, 0, _sem_cadeiras(ordered), ())
    state = _Apuracao(vagas, qe, ordered)
    state.quocientes()
    state.medias(FASE_MEDIA)
    state.medias(FASE_MEDIA_LIVRE)
    return state.resultado(validos)


class _Apuracao:
    def __init__(self, vagas: int, qe: int, listas: tuple[Lista, ...]) -> None:
        self._vagas = vagas
        self._qe = qe
        self._listas = listas
        self._qp = {lista.legenda: lista.votos // qe for lista in listas}
        self._usados = {lista.legenda: 0 for lista in listas}
        self._por_fase = {
            (lista.legenda, fase): 0
            for lista in listas
            for fase in (FASE_QUOCIENTE, FASE_MEDIA, FASE_MEDIA_LIVRE)
        }
        self._eleitos: list[Eleito] = []

    def quocientes(self) -> None:
        """The QP can add up to more than the seats when the QE drops a half (art. 106)."""
        for lista in self._listas:
            for _ in range(self._qp[lista.legenda]):
                if len(self._eleitos) >= self._vagas:
                    return
                proximo = self._proximo(lista)
                if proximo is None or 10 * proximo.votos < self._qe:
                    break
                self._eleger(lista, FASE_QUOCIENTE, empate_media=False)

    def medias(self, fase: str) -> None:
        while len(self._eleitos) < self._vagas:
            escolhida = self._maior_media(fase)
            if escolhida is None:
                return
            lista, empate = escolhida
            self._eleger(lista, fase, empate_media=empate)

    def resultado(self, validos: int) -> ResultadoProporcional:
        listas = tuple(
            ResultadoLista(
                lista.legenda,
                lista.votos,
                lista.votos_legenda,
                self._qp[lista.legenda],
                self._por_fase[(lista.legenda, FASE_QUOCIENTE)],
                self._por_fase[(lista.legenda, FASE_MEDIA)],
                self._por_fase[(lista.legenda, FASE_MEDIA_LIVRE)],
            )
            for lista in self._listas
        )
        return ResultadoProporcional(
            self._vagas, validos, self._qe, listas, self._com_empate_de_candidato()
        )

    def _maior_media(self, fase: str) -> tuple[Lista, bool] | None:
        candidatas = [lista for lista in self._listas if self._pode_disputar(lista, fase)]
        if not candidatas:
            return None
        chaves = {lista.legenda: self._chave(lista) for lista in candidatas}
        melhor = min(candidatas, key=lambda lista: (chaves[lista.legenda], lista.legenda))
        empatadas = sum(
            1 for lista in candidatas if chaves[lista.legenda] == chaves[melhor.legenda]
        )
        return melhor, empatadas > 1

    def _pode_disputar(self, lista: Lista, fase: str) -> bool:
        proximo = self._proximo(lista)
        if proximo is None:
            return False
        if fase == FASE_MEDIA_LIVRE:
            return True
        return 5 * lista.votos >= 4 * self._qe and 5 * proximo.votos >= self._qe

    def _chave(self, lista: Lista) -> tuple[Fraction, int, int]:
        """Sorts ascending: the highest average, list votes and next-candidate votes come first."""
        proximo = self._proximo(lista)
        votos_proximo = proximo.votos if proximo is not None else 0
        return (-Fraction(lista.votos, self._divisor(lista)), -lista.votos, -votos_proximo)

    def _divisor(self, lista: Lista) -> int:
        legenda = lista.legenda
        medias = self._por_fase[(legenda, FASE_MEDIA)] + self._por_fase[(legenda, FASE_MEDIA_LIVRE)]
        return self._qp[legenda] + medias + 1

    def _proximo(self, lista: Lista) -> Candidato | None:
        usados = self._usados[lista.legenda]
        if usados >= len(lista.candidatos):
            return None
        return lista.candidatos[usados]

    def _eleger(self, lista: Lista, fase: str, *, empate_media: bool) -> None:
        usados = self._usados[lista.legenda]
        candidato = lista.candidatos[usados]
        self._usados[lista.legenda] = usados + 1
        self._por_fase[(lista.legenda, fase)] += 1
        self._eleitos.append(
            Eleito(
                lista.legenda,
                candidato.numero,
                candidato.partido,
                candidato.votos,
                fase,
                empate_media,
            )
        )

    def _com_empate_de_candidato(self) -> tuple[Eleito, ...]:
        """Flags the last elected candidate of a list who ties with the first one left out."""
        flagged: list[Eleito] = []
        for eleito in self._eleitos:
            lista = next(item for item in self._listas if item.legenda == eleito.legenda)
            usados = self._usados[lista.legenda]
            fora = lista.candidatos[usados] if usados < len(lista.candidatos) else None
            empate = fora is not None and fora.votos == eleito.votos
            flagged.append(replace(eleito, empate=eleito.empate or empate))
        return tuple(flagged)


def _sem_cadeiras(listas: tuple[Lista, ...]) -> tuple[ResultadoLista, ...]:
    """QE 0 (fewer valid votes than half the seats): nobody is elected, the lists still show."""
    return tuple(
        ResultadoLista(lista.legenda, lista.votos, lista.votos_legenda, 0, 0, 0, 0)
        for lista in listas
    )


def _require_count(value: int, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InvalidSeatRuleError(field)
