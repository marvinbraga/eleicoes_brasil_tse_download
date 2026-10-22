"""Ports for the stored votes per candidate number behind the seat estimate."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from eleicoes.domain.errors import InvalidStoredReportError
from eleicoes.domain.simulacao_cadeiras import VotoApurado


@dataclass(frozen=True, slots=True)
class StoredSeatVotes:
    cargo: str
    votos: tuple[VotoApurado, ...]
    gerado_em: datetime

    def __post_init__(self) -> None:
        if self.gerado_em.tzinfo is None:
            raise InvalidStoredReportError("gerado_em")
        if any(voto.cargo != self.cargo for voto in self.votos):
            raise InvalidStoredReportError("cargo")


class CandidateVoteSource(Protocol):
    def candidate_totals(self, ano: int, turno: int, cargo: str) -> tuple[VotoApurado, ...]: ...

    def close(self) -> None: ...


class SeatVoteStore(Protocol):
    def load(self, ano: int, turno: int) -> tuple[StoredSeatVotes, ...]: ...

    def generated_at(self, ano: int, turno: int, cargo: str) -> datetime | None: ...

    def save(
        self, ano: int, turno: int, cargo: str, votos: tuple[VotoApurado, ...]
    ) -> datetime: ...

    def close(self) -> None: ...


class AsyncSeatVoteStore(Protocol):
    async def load(self, ano: int, turno: int) -> tuple[StoredSeatVotes, ...]: ...
