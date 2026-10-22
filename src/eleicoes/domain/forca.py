"""Party strength scoreboard from stored power cells. Counts stay integers; the page divides."""

import re
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Final

from eleicoes.domain.errors import InvalidCargoError
from eleicoes.domain.stored_grade import StoredCell
from eleicoes.domain.values import uf_name

CARGOS_REFERENCIA: Final[tuple[str, ...]] = (
    "presidente",
    "governador",
    "senador",
    "deputadoFederal",
    "deputadoEstadual",
)
LIMIARES: Final[tuple[int, ...]] = (1, 2, 5, 10, 20)
PAIS: Final = "BR"
EXTERIOR: Final = "ZZ"
_MUNICIPIO: Final = "municipio"
_UF: Final = "uf"
_PAIS_NIVEL: Final = "pais"
_PAIS_NOME: Final = "Brasil"
_SUFIXO: Final = re.compile(r" \(([A-Z]{2})\)$")
_SEM_PARTIDO: Final = 100  # above every party number (1-99): units without members sort last

Chave = Callable[[int], str]
Votos = dict[str, int]


def require_cargo_referencia(cargo: str) -> str:
    if cargo not in CARGOS_REFERENCIA:
        raise InvalidCargoError(cargo)
    return cargo


def uf_do_nome(nome: str) -> str | None:
    found = _SUFIXO.search(nome)
    return None if found is None else found.group(1)


def por_partido(partido: int) -> str:
    return str(partido)


def lider(votos: Mapping[str, int]) -> str | None:
    if not votos:
        return None
    topo = max(votos.values())
    if topo <= 0:
        return None
    primeiros = [chave for chave, valor in votos.items() if valor == topo]
    return primeiros[0] if len(primeiros) == 1 else None


@dataclass(frozen=True, slots=True)
class Cidade:
    codigo: str
    uf: str
    votos: tuple[tuple[str, int], ...]

    @property
    def validos(self) -> int:
        return sum(valor for _chave, valor in self.votos)


@dataclass(frozen=True, slots=True)
class Presenca:
    limiar: int
    municipios: int


@dataclass(frozen=True, slots=True)
class Municipal:
    lidera: int
    validos_liderados: int
    presenca: tuple[Presenca, ...]


@dataclass(frozen=True, slots=True)
class BaseMunicipal:
    municipios: int
    validos: int
    empates: int


MUNICIPAL_VAZIO: Final = Municipal(0, 0, tuple(Presenca(limiar, 0) for limiar in LIMIARES))


def _validos_da_celula(cell: StoredCell) -> int:
    return cell.votos_nominais + cell.votos_legenda


def somar(cells: Iterable[StoredCell], chave: Chave) -> dict[str, int]:
    totais: dict[str, int] = {}
    for cell in cells:
        nome = chave(cell.partido)
        totais[nome] = totais.get(nome, 0) + _validos_da_celula(cell)
    return totais


def cidades(cells: Iterable[StoredCell], chave: Chave = por_partido) -> tuple[Cidade, ...]:
    grupos: dict[str, list[StoredCell]] = {}
    ufs: dict[str, str] = {}
    for cell in cells:
        uf = uf_do_nome(cell.nome) if cell.nivel == _MUNICIPIO else None
        if uf is None or uf == EXTERIOR:
            continue
        grupos.setdefault(cell.codigo, []).append(cell)
        ufs[cell.codigo] = uf
    return tuple(
        Cidade(codigo, ufs[codigo], tuple(sorted(somar(items, chave).items())))
        for codigo, items in grupos.items()
    )


def resumo_municipal(lista: Iterable[Cidade]) -> tuple[BaseMunicipal, dict[str, Municipal]]:
    pares = tuple((cidade, cidade.validos) for cidade in lista)
    validas = tuple((cidade, validos) for cidade, validos in pares if validos > 0)
    conta = _Contagem()
    for cidade, validos in validas:
        conta.adicionar(cidade, validos)
    base = BaseMunicipal(len(validas), sum(validos for _cidade, validos in validas), conta.empates)
    return base, conta.municipais()


class _Contagem:
    def __init__(self) -> None:
        self.empates = 0
        self._lidera: dict[str, int] = {}
        self._liderados: dict[str, int] = {}
        self._presenca: dict[str, list[int]] = {}
        self._votos: dict[str, int] = {}

    def adicionar(self, cidade: Cidade, validos: int) -> None:
        votos = dict(cidade.votos)
        primeiro = lider(votos)
        if primeiro is None:
            self.empates += 1
        else:
            self._lidera[primeiro] = self._lidera.get(primeiro, 0) + 1
            self._liderados[primeiro] = self._liderados.get(primeiro, 0) + validos
        for chave, valor in votos.items():
            self._votos[chave] = self._votos.get(chave, 0) + valor
            self._marcar(chave, valor, validos)

    def _marcar(self, chave: str, valor: int, validos: int) -> None:
        contagem = self._presenca.setdefault(chave, [0] * len(LIMIARES))
        for indice, limiar in enumerate(LIMIARES):
            if valor > 0 and valor * 100 >= limiar * validos:
                contagem[indice] += 1

    def municipais(self) -> dict[str, Municipal]:
        positivas = (chave for chave, total in self._votos.items() if total > 0)
        return {chave: self._municipal(chave) for chave in positivas}

    def _municipal(self, chave: str) -> Municipal:
        pares = zip(LIMIARES, self._presenca[chave], strict=True)
        presenca = tuple(Presenca(limiar, n) for limiar, n in pares)
        return Municipal(self._lidera.get(chave, 0), self._liderados.get(chave, 0), presenca)


@dataclass(frozen=True, slots=True)
class FontesForca:
    presidente: tuple[StoredCell, ...] | None
    deputado_federal: tuple[StoredCell, ...] | None
    deputado_estadual: tuple[StoredCell, ...] | None
    referencia: tuple[StoredCell, ...] | None


@dataclass(frozen=True, slots=True)
class BaseRecorte:
    validos_presidente: int | None
    validos_deputado_federal: int | None
    validos_deputado_estadual: int | None
    ufs_deputado_estadual: int | None
    municipal: BaseMunicipal | None


@dataclass(frozen=True, slots=True)
class ForcaUnidade:
    chave: str
    partidos: tuple[int, ...]
    presidente: int | None
    deputado_federal: int | None
    deputado_estadual: int | None
    ufs_lider_estadual: int | None
    municipal: Municipal | None


@dataclass(frozen=True, slots=True)
class Recorte:
    codigo: str
    nome: str
    base: BaseRecorte
    unidades: tuple[ForcaUnidade, ...]


@dataclass(frozen=True, slots=True)
class PlacarForca:
    ano: int
    turno: int
    cargo_referencia: str
    limiares: tuple[int, ...]
    pais: Recorte
    ufs: tuple[Recorte, ...]
    faltando: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _Fonte:
    lugares: Mapping[tuple[str, str], Votos]
    presentes: frozenset[str]

    def votos(self, nivel: str, codigo: str) -> Votos | None:
        return self.lugares.get((nivel, codigo))

    def codigos(self, nivel: str) -> tuple[str, ...]:
        return tuple(codigo for chave_nivel, codigo in self.lugares if chave_nivel == nivel)


@dataclass(frozen=True, slots=True)
class _Lugar:
    presidente: Votos | None
    deputado_federal: Votos | None
    deputado_estadual: Votos | None
    lideres_estaduais: Votos | None
    municipal: tuple[BaseMunicipal, dict[str, Municipal]] | None


def placar_forca(
    ano: int,
    turno: int,
    cargo_referencia: str,
    fontes: FontesForca,
    chave: Chave = por_partido,
) -> PlacarForca:
    cargo = require_cargo_referencia(cargo_referencia)
    contexto = _Contexto(fontes, chave)
    pais = contexto.recorte_pais()
    ufs = tuple(contexto.recorte_uf(uf) for uf in contexto.ufs())
    return PlacarForca(ano, turno, cargo, LIMIARES, pais, ufs, _faltando(cargo, fontes))


class _Contexto:
    def __init__(self, fontes: FontesForca, chave: Chave) -> None:
        referencia = fontes.referencia
        self._pres = _fonte(fontes.presidente, chave)
        self._fed = _fonte(fontes.deputado_federal, chave)
        self._est = _fonte(fontes.deputado_estadual, chave)
        self._ref = None if referencia is None else frozenset(chave(c.partido) for c in referencia)
        self._cidades = None if referencia is None else _por_uf(cidades(referencia, chave))
        self._estaduais = _estaduais(self._est)
        self._membros = _membros(fontes, chave)

    def ufs(self) -> tuple[str, ...]:
        codigos: set[str] = set(self._estaduais)
        for fonte in (self._pres, self._fed):
            if fonte is not None:
                codigos.update(fonte.codigos(_UF))
        if self._cidades is not None:
            codigos.update(self._cidades)
        codigos.discard(EXTERIOR)
        return tuple(sorted(codigos))

    def recorte_pais(self) -> Recorte:
        sem_fonte = self._est is None
        estadual = None if sem_fonte or not self._estaduais else _soma(self._estaduais.values())
        lugar = _Lugar(
            _at(self._pres, _PAIS_NIVEL, PAIS),
            _at(self._fed, _PAIS_NIVEL, PAIS),
            estadual,
            None if sem_fonte else _lideres(self._estaduais),
            self._municipal(None),
        )
        quantas = None if sem_fonte else len(self._estaduais)
        return Recorte(PAIS, _PAIS_NOME, self._base(lugar, quantas), self._unidades(lugar))

    def recorte_uf(self, uf: str) -> Recorte:
        estadual = self._estaduais.get(uf)
        lugar = _Lugar(
            _at(self._pres, _UF, uf),
            _at(self._fed, _UF, uf),
            estadual,
            None if estadual is None else _lideres({uf: estadual}),
            self._municipal(uf),
        )
        quantas = None if estadual is None else 1
        return Recorte(uf, uf_name(uf), self._base(lugar, quantas), self._unidades(lugar))

    def _municipal(self, uf: str | None) -> tuple[BaseMunicipal, dict[str, Municipal]] | None:
        if self._cidades is None:
            return None
        if uf is None:
            lista = [cidade for grupo in self._cidades.values() for cidade in grupo]
        else:
            lista = self._cidades.get(uf, [])
        return resumo_municipal(lista) if lista else None

    def _base(self, lugar: _Lugar, quantas: int | None) -> BaseRecorte:
        municipal = None if lugar.municipal is None else lugar.municipal[0]
        return BaseRecorte(
            _validos(lugar.presidente),
            _validos(lugar.deputado_federal),
            _validos(lugar.deputado_estadual),
            quantas,
            municipal,
        )

    def _unidades(self, lugar: _Lugar) -> tuple[ForcaUnidade, ...]:
        municipais = None if lugar.municipal is None else lugar.municipal[1]
        votos = (lugar.presidente, lugar.deputado_federal, lugar.deputado_estadual)
        chaves = _positivas(votos, municipais)
        unidades = (self._unidade(chave, lugar, municipais) for chave in chaves)
        return tuple(sorted(unidades, key=_ordem_unidade))

    def _unidade(
        self,
        chave: str,
        lugar: _Lugar,
        municipais: dict[str, Municipal] | None,
    ) -> ForcaUnidade:
        return ForcaUnidade(
            chave,
            self._membros.get(chave, ()),
            _valor(self._pres, lugar.presidente, chave),
            _valor(self._fed, lugar.deputado_federal, chave),
            _valor(self._est, lugar.deputado_estadual, chave),
            _valor(self._est, lugar.lideres_estaduais, chave),
            _municipal_de(self._ref, municipais, chave),
        )


def _fonte(cells: tuple[StoredCell, ...] | None, chave: Chave) -> _Fonte | None:
    if cells is None:
        return None
    lugares: dict[tuple[str, str], Votos] = {}
    for cell in cells:
        if cell.nivel == _MUNICIPIO:
            continue
        votos = lugares.setdefault((cell.nivel, cell.codigo), {})
        nome = chave(cell.partido)
        votos[nome] = votos.get(nome, 0) + _validos_da_celula(cell)
    return _Fonte(lugares, frozenset(chave(cell.partido) for cell in cells))


def _estaduais(fonte: _Fonte | None) -> dict[str, Votos]:
    if fonte is None:
        return {}
    return {
        codigo: votos
        for (nivel, codigo), votos in fonte.lugares.items()
        if nivel == _UF and codigo != EXTERIOR and sum(votos.values()) > 0
    }


def _por_uf(lista: tuple[Cidade, ...]) -> dict[str, list[Cidade]]:
    grupos: dict[str, list[Cidade]] = {}
    for cidade in lista:
        grupos.setdefault(cidade.uf, []).append(cidade)
    return grupos


def _membros(fontes: FontesForca, chave: Chave) -> dict[str, tuple[int, ...]]:
    grupos: dict[str, set[int]] = {}
    todas = (
        fontes.presidente,
        fontes.deputado_federal,
        fontes.deputado_estadual,
        fontes.referencia,
    )
    for cells in todas:
        for cell in cells or ():
            grupos.setdefault(chave(cell.partido), set()).add(cell.partido)
    return {nome: tuple(sorted(partidos)) for nome, partidos in grupos.items()}


def _at(fonte: _Fonte | None, nivel: str, codigo: str) -> Votos | None:
    return None if fonte is None else fonte.votos(nivel, codigo)


def _soma(lista: Iterable[Votos]) -> Votos:
    total: Votos = {}
    for votos in lista:
        for chave, valor in votos.items():
            total[chave] = total.get(chave, 0) + valor
    return total


def _lideres(por_uf: Mapping[str, Votos]) -> Votos:
    contagem = Counter(primeiro for primeiro in map(lider, por_uf.values()) if primeiro is not None)
    return dict(contagem)


def _validos(votos: Votos | None) -> int | None:
    return None if votos is None else sum(votos.values())


def _positivas(
    lista: tuple[Votos | None, ...],
    municipais: dict[str, Municipal] | None,
) -> set[str]:
    chaves = {chave for votos in lista for chave, valor in (votos or {}).items() if valor > 0}
    if municipais is not None:
        chaves.update(municipais)
    return chaves


def _valor(fonte: _Fonte | None, votos: Votos | None, chave: str) -> int | None:
    if fonte is None or votos is None or chave not in fonte.presentes:
        return None
    return votos.get(chave, 0)


def _municipal_de(
    presentes: frozenset[str] | None,
    municipais: dict[str, Municipal] | None,
    chave: str,
) -> Municipal | None:
    if presentes is None or municipais is None or chave not in presentes:
        return None
    return municipais.get(chave, MUNICIPAL_VAZIO)


def _ordem_unidade(unidade: ForcaUnidade) -> tuple[int, str]:
    return (unidade.partidos[0] if unidade.partidos else _SEM_PARTIDO, unidade.chave)


def _faltando(cargo: str, fontes: FontesForca) -> tuple[str, ...]:
    pares = (
        ("presidente", fontes.presidente),
        ("deputadoFederal", fontes.deputado_federal),
        ("deputadoEstadual", fontes.deputado_estadual),
        (cargo, fontes.referencia),
    )
    faltam = {nome for nome, cells in pares if cells is None}
    return tuple(nome for nome in CARGOS_REFERENCIA if nome in faltam)
