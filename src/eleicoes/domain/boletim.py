"""Boletim de urna e a linha de voto. Sem IO."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Final

from eleicoes.domain.errors import InvalidBoletimContentError
from eleicoes.domain.report import EXIT_NOT_PUBLISHED, EXIT_SUCCESS
from eleicoes.domain.values import ElectionYear, Turno, Uf

_INT_MAX: Final = 2_147_483_647
_STAMP_FORMAT: Final = "%Y%m%dT%H%M%S"
_CONSULTA_MIN: Final = 25
_CONSULTA_MAX: Final = 99
_TIPOS_CARGO: Final = frozenset({"majoritario", "proporcional", "consulta"})
_TIPOS_VOTO: Final = frozenset({"nominal", "branco", "nulo", "legenda", "cargoSemCandidato"})
_UNNUMBERED: Final = frozenset({"branco", "nulo"})
_NUMBERED: Final = frozenset({"nominal", "legenda"})
_CONSTITUTIONAL_CARGOS: Final = frozenset(
    {
        "presidente",
        "vicePresidente",
        "governador",
        "viceGovernador",
        "senador",
        "deputadoFederal",
        "deputadoEstadual",
        "deputadoDistrital",
        "primeiroSuplenteSenador",
        "segundoSuplenteSenador",
        "prefeito",
        "vicePrefeito",
        "vereador",
    }
)
_OFFICIAL: Final = "oficial"


@dataclass(frozen=True, slots=True)
class VoteLine:
    """Uma linha de voto. Branco e nulo não têm partido nem número."""

    id_eleicao: int
    eleitores_aptos: int
    qtd_comparecimento: int
    qtd_eleitores_complemento: int
    tipo_cargo: str
    cargo: str
    ordem_impressao: int
    comparecimento_cargo: int
    tipo_voto: str
    partido: int | None
    numero: int | None
    quantidade: int

    def __post_init__(self) -> None:
        _require_election_ids(self)
        _require_vote_kind(self)
        _require_identification(self)


@dataclass(frozen=True, slots=True)
class Boletim:
    """Boletim de uma seção. Ano, turno e UF vêm do comando, não do arquivo."""

    arquivo: str
    fase: str
    municipio: int
    zona: int
    local: int
    secao: int
    data_hora_emissao: str
    versao_urna: str
    numero_interno_urna: int
    data_hora_carga: str
    codigo_carga: str
    codigo_midia: str
    eleitores_computados: int
    indicador_habilitacao: int
    qtd_biometria: int
    qtd_manual: int
    votos: tuple[VoteLine, ...]

    def __post_init__(self) -> None:
        _require_arquivo(self.arquivo)
        _require_fase(self.fase)
        _require_section(self)
        _require_machine(self)
        _require_counts(self)
        _require_stamp(self.data_hora_emissao, "data_hora_emissao")
        _require_stamp(self.data_hora_carga, "data_hora_carga")
        _require_consistent(self.votos)

    def lines_for(self, id_eleicao: int, cargo: str) -> tuple[VoteLine, ...]:
        return tuple(
            line for line in self.votos if line.id_eleicao == id_eleicao and line.cargo == cargo
        )

    def total_for(self, id_eleicao: int, cargo: str) -> int:
        return sum(line.quantidade for line in self.lines_for(id_eleicao, cargo))


@dataclass(frozen=True, slots=True)
class ImportBoletinsCommand:
    year: ElectionYear
    turno: Turno
    uf: Uf
    origin: Path


@dataclass(frozen=True, slots=True)
class BoletimImportReport:
    boletins: int
    votos: int

    @property
    def exit_code(self) -> int:
        if self.boletins == 0:
            return EXIT_NOT_PUBLISHED
        return EXIT_SUCCESS


def _require_election_ids(line: VoteLine) -> None:
    _require_range(line.id_eleicao, 0, 99999, "id_eleicao")
    _require_range(line.eleitores_aptos, 0, 9999, "eleitores_aptos")
    _require_range(line.qtd_comparecimento, 0, 9999, "qtd_comparecimento")
    _require_range(line.qtd_eleitores_complemento, 0, _INT_MAX, "qtd_eleitores_complemento")


def _require_vote_kind(line: VoteLine) -> None:
    if line.tipo_cargo not in _TIPOS_CARGO:
        raise InvalidBoletimContentError("tipo_cargo")
    if line.tipo_voto not in _TIPOS_VOTO:
        raise InvalidBoletimContentError("tipo_voto")
    _require_range(line.quantidade, 0, 9999, "quantidade")
    _require_range(line.comparecimento_cargo, 0, 9999, "comparecimento_cargo")
    _require_range(line.ordem_impressao, 1, 99, "ordem_impressao")
    _require_cargo_name(line.cargo)


def _require_identification(line: VoteLine) -> None:
    present = line.partido is not None or line.numero is not None
    complete = line.partido is not None and line.numero is not None
    if line.tipo_voto in _UNNUMBERED and present:
        raise InvalidBoletimContentError("identificacao")
    if line.tipo_voto in _NUMBERED and not complete:
        raise InvalidBoletimContentError("identificacao")
    if present and not complete:
        raise InvalidBoletimContentError("identificacao")
    if line.partido is not None:
        _require_range(line.partido, 0, 99, "partido")
    if line.numero is not None:
        _require_range(line.numero, 0, 99999, "numero")


def _require_cargo_name(cargo: str) -> None:
    if cargo in _CONSTITUTIONAL_CARGOS:
        return
    if not cargo.isdigit():
        raise InvalidBoletimContentError("cargo")
    number = int(cargo)
    if cargo != str(number) or number < _CONSULTA_MIN or number > _CONSULTA_MAX:
        raise InvalidBoletimContentError("cargo")


def _require_arquivo(arquivo: str) -> None:
    path = PurePosixPath(arquivo)
    if (
        not arquivo
        or "\\" in arquivo
        or arquivo.startswith("/")
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise InvalidBoletimContentError("arquivo")


def _require_fase(fase: str) -> None:
    if fase != _OFFICIAL:
        raise InvalidBoletimContentError("fase")


def _require_section(boletim: Boletim) -> None:
    _require_range(boletim.municipio, 1, 99999, "municipio")
    _require_range(boletim.zona, 1, 9999, "zona")
    _require_range(boletim.local, 1, 9999, "local")
    _require_range(boletim.secao, 1, 9999, "secao")


def _require_machine(boletim: Boletim) -> None:
    _require_token(boletim.versao_urna, "versao_urna")
    _require_range(boletim.numero_interno_urna, 0, 99_999_999, "numero_interno_urna")
    _require_token(boletim.codigo_carga, "codigo_carga")
    _require_token(boletim.codigo_midia, "codigo_midia")


def _require_counts(boletim: Boletim) -> None:
    _require_range(boletim.eleitores_computados, 0, _INT_MAX, "eleitores_computados")
    _require_range(boletim.indicador_habilitacao, 0, _INT_MAX, "indicador_habilitacao")
    _require_range(boletim.qtd_biometria, 0, _INT_MAX, "qtd_biometria")
    _require_range(boletim.qtd_manual, 0, _INT_MAX, "qtd_manual")


def _require_consistent(lines: tuple[VoteLine, ...]) -> None:
    elections: dict[int, tuple[int, int, int]] = {}
    cargos: dict[tuple[int, str], tuple[str, int, int]] = {}
    for line in lines:
        _require_same_election(elections, line)
        _require_same_cargo(cargos, line)


def _require_same_election(seen: dict[int, tuple[int, int, int]], line: VoteLine) -> None:
    stamp = (line.eleitores_aptos, line.qtd_comparecimento, line.qtd_eleitores_complemento)
    previous = seen.get(line.id_eleicao)
    if previous is None:
        seen[line.id_eleicao] = stamp
        return
    if previous != stamp:
        raise InvalidBoletimContentError("eleicao")


def _require_same_cargo(
    seen: dict[tuple[int, str], tuple[str, int, int]],
    line: VoteLine,
) -> None:
    stamp = (line.tipo_cargo, line.ordem_impressao, line.comparecimento_cargo)
    previous = seen.get((line.id_eleicao, line.cargo))
    if previous is None:
        seen[(line.id_eleicao, line.cargo)] = stamp
        return
    if previous != stamp:
        raise InvalidBoletimContentError("cargo")


def _require_stamp(value: str, field: str) -> None:
    try:
        datetime.strptime(value, _STAMP_FORMAT)
    except ValueError as exc:
        raise InvalidBoletimContentError(field) from exc


def _require_token(value: str, field: str) -> None:
    if not value or value != value.strip() or any(char in value for char in "\n\r\t"):
        raise InvalidBoletimContentError(field)


def _require_range(value: int, low: int, high: int, field: str) -> None:
    if isinstance(value, bool) or value < low or value > high:
        raise InvalidBoletimContentError(field)
