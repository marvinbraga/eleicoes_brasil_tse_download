from typing import Protocol

from eleicoes.domain.values import ElectionYear


class TotalizacaoPublication(Protocol):
    def is_published(self, year: ElectionYear) -> bool: ...
