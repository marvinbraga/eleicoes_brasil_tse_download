"""Partidos e federações de cada eleição geral. Na proporcional, a federação é uma lista só.

Fontes de 2026 (conferidas em 2026-10-22):
- https://www.tse.jus.br/partidos/federacoes-registradas-no-tse
- https://www.tse.jus.br/comunicacao/noticias/2025/Dezembro/tse-aprova-criacao-da-federacao-renovacao-solidaria
- https://www.tse.jus.br/comunicacao/noticias/2026/Marco/tse-aprova-registro-da-federacao-uniao-progressista-1
- Lista de partidos, federações e candidaturas do 1º turno (DJE-TSE, 18/09/2026):
  https://sintse.tse.jus.br/documentos/2026/Set/23/diario-da-justica-eletronico-tres-destaques-edicoes-anteriores/lista-de-partidos-federacoes-coligacoes-candidatas-e-candidatos-eleicao-geral-federal-2026-1o-turno

Para atualizar: edite REGISTROS, rode os testes e reinicie a API. Os votos gravados
não mudam; as cadeiras são recalculadas na leitura.
"""

from dataclasses import dataclass
from typing import Final

from eleicoes.domain.errors import InvalidSeatRuleError, UnknownPartyRegistryError

_MIN_PARTIDO: Final = 10
_MAX_PARTIDO: Final = 99
_MIN_MEMBROS: Final = 2


@dataclass(frozen=True, slots=True)
class Federacao:
    codigo: str
    sigla: str
    nome: str
    partidos: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.codigo.strip() or not self.sigla.strip() or not self.nome.strip():
            raise InvalidSeatRuleError("federacao")
        if self.codigo.isdigit():
            raise InvalidSeatRuleError("codigo")
        if len(self.partidos) < _MIN_MEMBROS or len(set(self.partidos)) != len(self.partidos):
            raise InvalidSeatRuleError("partidos")


@dataclass(frozen=True, slots=True)
class RegistroPartidario:
    ano: int
    partidos: frozenset[int]
    federacoes: tuple[Federacao, ...]

    def __post_init__(self) -> None:
        if any(p < _MIN_PARTIDO or p > _MAX_PARTIDO for p in self.partidos):
            raise InvalidSeatRuleError("partidos")
        seen: set[int] = set()
        codes: set[str] = set()
        for federacao in self.federacoes:
            members = set(federacao.partidos)
            if not members <= self.partidos or members & seen:
                raise InvalidSeatRuleError("federacao")
            if federacao.codigo in codes:
                raise InvalidSeatRuleError("codigo")
            seen |= members
            codes.add(federacao.codigo)

    def legenda(self, partido: int) -> str:
        """The proportional list a party competes in: a federation code or the party number."""
        federacao = self.federacao_de(partido)
        return federacao.codigo if federacao is not None else str(partido)

    def federacao_de(self, partido: int) -> Federacao | None:
        for federacao in self.federacoes:
            if partido in federacao.partidos:
                return federacao
        return None


REGISTRO_2026: Final = RegistroPartidario(
    ano=2026,
    partidos=frozenset(
        {
            10,
            11,
            12,
            13,
            14,
            15,
            16,
            18,
            20,
            21,
            22,
            23,
            25,
            27,
            28,
            29,
            30,
            33,
            35,
            36,
            40,
            43,
            44,
            45,
            50,
            55,
            65,
            70,
            77,
            80,
        }
    ),
    federacoes=(
        Federacao("fe-brasil", "FE BRASIL", "Federação Brasil da Esperança", (13, 65, 43)),
        Federacao("psdb-cidadania", "PSDB CIDADANIA", "Federação PSDB Cidadania", (45, 23)),
        Federacao("psol-rede", "PSOL REDE", "Federação PSOL Rede", (50, 18)),
        Federacao(
            "renovacao-solidaria",
            "RENOVAÇÃO SOLIDÁRIA",
            "Federação Renovação Solidária",
            (25, 77),
        ),
        Federacao(
            "uniao-progressista",
            "UNIÃO PROGRESSISTA",
            "Federação União Progressista",
            (44, 11),
        ),
    ),
)

REGISTROS: Final[dict[int, RegistroPartidario]] = {REGISTRO_2026.ano: REGISTRO_2026}


def registro_partidario(ano: int) -> RegistroPartidario:
    found = REGISTROS.get(ano)
    if found is None:
        raise UnknownPartyRegistryError(ano)
    return found
