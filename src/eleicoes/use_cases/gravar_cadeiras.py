"""Sum the votes per candidate number once per cargo and store them for the seat estimate.

The scan of raw.boletim is the slow part (minutes per cargo). Seats are not stored: the
API recalculates them from these votes, so a federation update needs no new scan.
"""

import argparse
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from eleicoes.domain.cadeiras import CARGOS_GRAVADOS, TURNO_SIMULADO
from eleicoes.domain.errors import (
    SCHEMA_OUTDATED_HINT,
    ElectionError,
    InvalidCargoError,
    SchemaOutdatedError,
)
from eleicoes.domain.federacoes import registro_partidario
from eleicoes.domain.percentual import format_integer
from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS
from eleicoes.domain.simulacao_cadeiras import SimulacaoCadeiras, simular_cadeiras
from eleicoes.domain.values import ElectionYear, Turno
from eleicoes.ports.relatorio_cadeiras import CandidateVoteSource, SeatVoteStore
from eleicoes.use_cases.failure import failure_line

_FAILURE: Final = "Não foi possível gravar os votos por candidato."
Announce = Callable[[str], None]


@dataclass(frozen=True, slots=True)
class RecordedCargo:
    cargo: str
    linhas: int | None
    gerado_em: datetime
    reaproveitado: bool


class RecordSeatVotes:
    def __init__(
        self,
        source: CandidateVoteSource,
        store: SeatVoteStore,
        announce: Announce | None = None,
    ) -> None:
        self._source = source
        self._store = store
        self._announce = announce or _silent

    def execute(
        self,
        ano: int,
        turno: int,
        cargos: Sequence[str] = CARGOS_GRAVADOS,
        *,
        atualizar: bool = False,
    ) -> tuple[RecordedCargo, ...]:
        year = ElectionYear(ano).value
        turn = Turno(turno).value
        return tuple(self._one(year, turn, _known(cargo), atualizar) for cargo in cargos)

    def _one(self, ano: int, turno: int, cargo: str, atualizar: bool) -> RecordedCargo:
        if not atualizar:
            found = self._store.generated_at(ano, turno, cargo)
            if found is not None:
                return RecordedCargo(cargo, None, found, True)
        self._announce(f"Somando os votos de {cargo} nos boletins...")
        votos = self._source.candidate_totals(ano, turno, cargo)
        moment = self._store.save(ano, turno, cargo, votos)
        return RecordedCargo(cargo, len(votos), moment, False)


def summary(simulacao: SimulacaoCadeiras) -> str:
    governo = simulacao.governo
    eleitos = sum(1 for item in governo.ufs if item.eleito is not None)
    return "\n".join(
        (
            f"Câmara: {_part(simulacao.camara.vagas_simuladas, simulacao.camara.vagas)} vagas.",
            "Assembleias: "
            f"{_part(simulacao.assembleias.vagas_simuladas, simulacao.assembleias.vagas)} vagas.",
            f"Senado: {_part(simulacao.senado.vagas_simuladas, simulacao.senado.vagas)} vagas.",
            f"Governadores eleitos no 1º turno: {eleitos} de {len(governo.ufs)} UFs.",
        )
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    source: CandidateVoteSource | None = None,
    store: SeatVoteStore | None = None,
) -> int:
    args = _parser().parse_args(argv)
    try:
        text = _run(args, source, store)
    except SchemaOutdatedError:
        print(SCHEMA_OUTDATED_HINT, file=sys.stderr)
        return EXIT_FAILURE
    except ElectionError as exc:
        print(failure_line(_FAILURE, exc), file=sys.stderr)
        return EXIT_FAILURE
    print(text)
    return EXIT_SUCCESS


def _run(
    args: argparse.Namespace,
    source: CandidateVoteSource | None,
    store: SeatVoteStore | None,
) -> str:
    opened_source = source if source is not None else _production_source()
    opened_store = store if store is not None else _production_store()
    try:
        cargos = tuple(args.cargo) if args.cargo else CARGOS_GRAVADOS
        recorded = RecordSeatVotes(opened_source, opened_store, _print).execute(
            args.ano, args.turno, cargos, atualizar=bool(args.atualizar)
        )
        stored = opened_store.load(args.ano, args.turno)
    finally:
        opened_source.close()
        opened_store.close()
    lines = [_line(item) for item in recorded]
    if {item.cargo for item in stored} >= set(CARGOS_GRAVADOS):
        votos = tuple(voto for item in stored for voto in item.votos)
        registro = registro_partidario(args.ano)
        lines.append(summary(simular_cadeiras(args.ano, args.turno, votos, registro)))
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Grava os votos por candidato que a simulação de cadeiras usa.",
    )
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument(
        "--turno",
        type=int,
        choices=[TURNO_SIMULADO],
        default=TURNO_SIMULADO,
        help="Só o 1º turno: as cadeiras se decidem nele.",
    )
    parser.add_argument(
        "--cargo",
        action="append",
        choices=CARGOS_GRAVADOS,
        help="Repita para mais de um cargo. Sem a opção, grava os cinco.",
    )
    parser.add_argument(
        "--atualizar",
        action="store_true",
        help="Soma os boletins de novo e substitui os votos gravados.",
    )
    return parser


def _line(item: RecordedCargo) -> str:
    stamp = item.gerado_em.astimezone().strftime("%Y-%m-%d %H:%M")
    if item.reaproveitado:
        return f"{item.cargo}: já gravado em {stamp}. Use --atualizar para somar de novo."
    linhas = format_integer(item.linhas or 0)
    return f"{item.cargo}: {linhas} números gravados em {stamp}."


def _part(simuladas: int, total: int) -> str:
    return f"{format_integer(simuladas)} de {format_integer(total)}"


def _known(cargo: str) -> str:
    if cargo not in CARGOS_GRAVADOS:
        raise InvalidCargoError(cargo)
    return cargo


def _print(message: str) -> None:
    print(message, flush=True)


def _silent(_message: str) -> None:
    return None


def _production_source() -> CandidateVoteSource:
    from eleicoes.composition.cadeiras import build_candidate_votes

    return build_candidate_votes()


def _production_store() -> SeatVoteStore:
    from eleicoes.composition.cadeiras import build_seat_vote_store

    return build_seat_vote_store()
