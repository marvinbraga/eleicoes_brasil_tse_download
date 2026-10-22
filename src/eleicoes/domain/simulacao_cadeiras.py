"""Seat estimate from stored first-round votes per candidate number. Pure; no IO.

A number whose prefix is not a registered party is treated as null and only counted in
descartados. Candidates whose registration was rejected cannot be told apart in the
boletim, so their votes stay valid here: this is an estimate, not the official result.
"""

from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Final, TypeAlias

from eleicoes.domain.boletim_consulta import partido_do_numero
from eleicoes.domain.cadeiras import (
    CARGO_CAMARA,
    CARGO_GOVERNO,
    CARGO_SENADO,
    CARGOS_GRAVADOS,
    cargo_assembleia,
    turno_simulado,
    ufs_com_vagas,
    vagas_assembleia,
    vagas_camara,
)
from eleicoes.domain.errors import InvalidNumeroError, InvalidSeatRuleError
from eleicoes.domain.federacoes import RegistroPartidario
from eleicoes.domain.majoritario import (
    VAGAS_SENADO_2026,
    ResultadoGoverno,
    ResultadoSenado,
    VotoCandidato,
    apurar_governo,
    eleger_senado,
)
from eleicoes.domain.proporcional import Candidato, Lista, ResultadoProporcional, distribuir
from eleicoes.domain.values import ElectionYear, Uf

CASA_CAMARA: Final = "camara"
CASA_ASSEMBLEIAS: Final = "assembleias"
_NOMINAL: Final = "nominal"
_LEGENDA: Final = "legenda"
_TIPOS: Final = frozenset({_NOMINAL, _LEGENDA})
_ABROAD: Final = "ZZ"


@dataclass(frozen=True, slots=True)
class VotoApurado:
    cargo: str
    uf: str
    tipo_voto: str
    numero: int
    votos: int

    def __post_init__(self) -> None:
        if self.cargo not in CARGOS_GRAVADOS:
            raise InvalidSeatRuleError("cargo")
        object.__setattr__(self, "uf", Uf(self.uf).code)
        if self.tipo_voto not in _TIPOS:
            raise InvalidSeatRuleError("tipo_voto")
        for value, field in ((self.numero, "numero"), (self.votos, "votos")):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise InvalidSeatRuleError(field)


@dataclass(frozen=True, slots=True)
class CasaUf:
    uf: str
    cargo: str
    resultado: ResultadoProporcional


@dataclass(frozen=True, slots=True)
class CasaSimulada:
    casa: str
    vagas: int
    ufs: tuple[CasaUf, ...]
    ufs_sem_votos: tuple[str, ...]

    @property
    def vagas_simuladas(self) -> int:
        return sum(item.resultado.vagas for item in self.ufs)

    def cadeiras_por_partido(self) -> dict[int, int]:
        counts: dict[int, int] = defaultdict(int)
        for item in self.ufs:
            for eleito in item.resultado.eleitos:
                counts[eleito.partido] += 1
        return dict(counts)

    def cadeiras_por_legenda(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for item in self.ufs:
            for eleito in item.resultado.eleitos:
                counts[eleito.legenda] += 1
        return dict(counts)


@dataclass(frozen=True, slots=True)
class SenadoSimulado:
    vagas: int
    ufs: tuple[ResultadoSenado, ...]
    ufs_sem_votos: tuple[str, ...]

    @property
    def vagas_simuladas(self) -> int:
        """Seats of the UFs with votes, as in the houses: a seat left without a candidate counts."""
        return sum(item.vagas for item in self.ufs)

    def cadeiras_por_partido(self) -> dict[int, int]:
        counts: dict[int, int] = defaultdict(int)
        for item in self.ufs:
            for eleito in item.eleitos:
                counts[eleito.partido] += 1
        return dict(counts)


@dataclass(frozen=True, slots=True)
class GovernoSimulado:
    ufs: tuple[ResultadoGoverno, ...]
    ufs_sem_votos: tuple[str, ...]

    def eleitos_por_partido(self) -> dict[int, int]:
        counts: dict[int, int] = defaultdict(int)
        for item in self.ufs:
            if item.eleito is not None:
                counts[item.eleito.partido] += 1
        return dict(counts)

    def segundo_turno_por_partido(self) -> dict[int, int]:
        counts: dict[int, int] = defaultdict(int)
        for item in self.ufs:
            for finalista in item.finalistas:
                counts[finalista.partido] += 1
        return dict(counts)


@dataclass(frozen=True, slots=True)
class ForcaPartido:
    """One row of the contract the força partidária scoreboard reads."""

    partido: int
    legenda: str
    camara: int
    assembleias: int
    senado: int
    governadores: int
    governadores_segundo_turno: int


@dataclass(frozen=True, slots=True)
class SimulacaoCadeiras:
    ano: int
    turno: int
    registro: RegistroPartidario
    camara: CasaSimulada
    assembleias: CasaSimulada
    senado: SenadoSimulado
    governo: GovernoSimulado
    descartados: int

    def partidos(self) -> tuple[ForcaPartido, ...]:
        camara = self.camara.cadeiras_por_partido()
        assembleias = self.assembleias.cadeiras_por_partido()
        senado = self.senado.cadeiras_por_partido()
        eleitos = self.governo.eleitos_por_partido()
        segundo = self.governo.segundo_turno_por_partido()
        found = set(camara) | set(assembleias) | set(senado) | set(eleitos) | set(segundo)
        rows = (
            ForcaPartido(
                partido,
                self.registro.legenda(partido),
                camara.get(partido, 0),
                assembleias.get(partido, 0),
                senado.get(partido, 0),
                eleitos.get(partido, 0),
                segundo.get(partido, 0),
            )
            for partido in found
        )
        return tuple(
            sorted(
                rows,
                key=lambda row: (
                    -row.camara,
                    -row.assembleias,
                    -row.senado,
                    -row.governadores,
                    -row.governadores_segundo_turno,
                    row.partido,
                ),
            )
        )


def simular_cadeiras(
    ano: int,
    turno: int,
    votos: Sequence[VotoApurado],
    registro: RegistroPartidario,
) -> SimulacaoCadeiras:
    year = ElectionYear(ano).value
    if registro.ano != year:
        raise InvalidSeatRuleError("ano")
    validos, descartados = _split(votos, registro)
    by_cargo_uf: dict[tuple[str, str], list[VotoApurado]] = defaultdict(list)
    for voto in validos:
        by_cargo_uf[(voto.cargo, voto.uf)].append(voto)
    ufs = ufs_com_vagas()
    return SimulacaoCadeiras(
        year,
        turno_simulado(turno),
        registro,
        _casa(CASA_CAMARA, ufs, _cargo_camara, vagas_camara, by_cargo_uf, registro),
        _casa(CASA_ASSEMBLEIAS, ufs, cargo_assembleia, vagas_assembleia, by_cargo_uf, registro),
        _senado(ufs, by_cargo_uf),
        _governo(ufs, by_cargo_uf),
        descartados,
    )


def _cargo_camara(_uf: str) -> str:
    return CARGO_CAMARA


def _split(
    votos: Iterable[VotoApurado], registro: RegistroPartidario
) -> tuple[list[VotoApurado], int]:
    kept: list[VotoApurado] = []
    dropped = 0
    for voto in votos:
        if voto.uf == _ABROAD or _partido(voto) not in registro.partidos:
            dropped += voto.votos
            continue
        kept.append(voto)
    return kept, dropped


def _partido(voto: VotoApurado) -> int | None:
    try:
        return partido_do_numero(voto.tipo_voto, voto.numero)
    except InvalidNumeroError:
        return None


_Grouped: TypeAlias = dict[tuple[str, str], list[VotoApurado]]


def _casa(
    casa: str,
    ufs: tuple[str, ...],
    cargo_of: Callable[[str], str],
    vagas_of: Callable[[str], int],
    by_cargo_uf: _Grouped,
    registro: RegistroPartidario,
) -> CasaSimulada:
    found: list[CasaUf] = []
    missing: list[str] = []
    for uf in ufs:
        cargo = cargo_of(uf)
        rows = by_cargo_uf.get((cargo, uf), [])
        if not rows:
            missing.append(uf)
            continue
        found.append(CasaUf(uf, cargo, distribuir(vagas_of(uf), _listas(rows, registro))))
    total = sum(vagas_of(uf) for uf in ufs)
    return CasaSimulada(casa, total, tuple(found), tuple(missing))


def _listas(rows: Sequence[VotoApurado], registro: RegistroPartidario) -> tuple[Lista, ...]:
    legenda: dict[str, int] = defaultdict(int)
    nominais: dict[str, list[Candidato]] = defaultdict(list)
    for row in rows:
        party = partido_do_numero(row.tipo_voto, row.numero)
        key = registro.legenda(party)
        if row.tipo_voto == _LEGENDA:
            legenda[key] += row.votos
        else:
            nominais[key].append(Candidato(row.numero, party, row.votos))
    keys = sorted(set(legenda) | set(nominais))
    return tuple(Lista(key, legenda.get(key, 0), tuple(nominais.get(key, []))) for key in keys)


def _majoritarios(rows: Sequence[VotoApurado]) -> tuple[VotoCandidato, ...]:
    return tuple(
        VotoCandidato(row.numero, partido_do_numero(_NOMINAL, row.numero), row.votos)
        for row in rows
        if row.tipo_voto == _NOMINAL
    )


def _senado(ufs: tuple[str, ...], by_cargo_uf: _Grouped) -> SenadoSimulado:
    found: list[ResultadoSenado] = []
    missing: list[str] = []
    for uf in ufs:
        rows = _majoritarios(by_cargo_uf.get((CARGO_SENADO, uf), []))
        if not rows:
            missing.append(uf)
            continue
        found.append(eleger_senado(uf, rows))
    return SenadoSimulado(VAGAS_SENADO_2026 * len(ufs), tuple(found), tuple(missing))


def _governo(ufs: tuple[str, ...], by_cargo_uf: _Grouped) -> GovernoSimulado:
    found: list[ResultadoGoverno] = []
    missing: list[str] = []
    for uf in ufs:
        rows = _majoritarios(by_cargo_uf.get((CARGO_GOVERNO, uf), []))
        if not rows:
            missing.append(uf)
            continue
        found.append(apurar_governo(uf, rows))
    return GovernoSimulado(tuple(found), tuple(missing))


NOTAS: Final[tuple[str, ...]] = (
    "É uma estimativa feita com os votos do 1º turno gravados nos boletins de urna. "
    "Não é o resultado oficial do TSE.",
    "Votos em candidatos com registro indeferido ou sub judice contam como válidos aqui. "
    "Na totalização oficial eles são anulados, o que muda o quociente eleitoral.",
    "Na Câmara e nas Assembleias, a federação conta como um partido só. A cadeira fica "
    "com o partido do número do candidato eleito.",
    "As sobras seguem o STF (ADIs 7228, 7263 e 7325): primeiro as legendas com 80% do "
    "quociente e candidato com 20%; depois todas, pelas maiores médias.",
    "Empate entre candidatos se decide pela idade, que o boletim não traz: a estimativa "
    "usa o menor número. Empate total entre listas fica com a de menor código. Os dois "
    "casos aparecem marcados.",
    "Governador: mais da metade dos votos válidos elege no 1º turno. Senado: os dois "
    "mais votados de cada UF.",
)
