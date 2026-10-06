"""Findings over correspondence projections. Rules run here, not in the adapter."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import Final

from eleicoes.domain.correspondencia.checks import require_text
from eleicoes.domain.correspondencia.projecao import ProjecaoContingencia, ProjecaoSecao
from eleicoes.domain.correspondencia.records import Referencia
from eleicoes.domain.correspondencia.statistics import median, median_absolute_deviation, modified_z
from eleicoes.domain.correspondencia.status import StatusCorrespondencia
from eleicoes.domain.correspondencia.tokens import is_blank_token
from eleicoes.domain.values import Uf

MODIFIED_Z_THRESHOLD: Final = 3.5
MIN_RATE_POPULATION: Final = 10
MIN_OUTLIER_EVENTS: Final = 2
MIN_ALTERED_SECTIONS_IN_UF: Final = 5
MIN_MACHINE_ALTERED_SECTIONS: Final = 4
MIN_MACHINE_SHARE: Final = 0.5


class Gravidade(Enum):
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAIXA = "BAIXA"


_GRAVITY_ORDER: Final = {
    Gravidade.ALTA: 0,
    Gravidade.MEDIA: 1,
    Gravidade.BAIXA: 2,
}


@dataclass(frozen=True, slots=True)
class Indicio:
    codigo: str
    descricao: str
    gravidade: Gravidade
    uf: str
    municipio: str
    medida: str
    referencias: tuple[Referencia, ...]

    def __post_init__(self) -> None:
        require_text(self.codigo, "codigo")
        require_text(self.descricao, "descricao")
        require_text(self.medida, "medida")
        if self.uf:
            object.__setattr__(self, "uf", Uf(self.uf).code)


class MapaDeIndicios:
    """One pass over sections and contingency urns, then the fixed rule set."""

    def avaliar(
        self,
        secoes: Iterable[ProjecaoSecao],
        contingencias: Iterable[ProjecaoContingencia],
    ) -> tuple[Indicio, ...]:
        quadro = _Quadro()
        for secao in secoes:
            quadro.registrar_secao(secao)
        for item in contingencias:
            quadro.registrar_contingencia(item)
        found = (
            *_shared_cargos(quadro),
            *_shared_urns(quadro),
            *_atypical_alteration_rates(quadro),
            *_concentrated_machines(quadro),
            *_new_sections(quadro),
            *_concentrated_new_contingencies(quadro),
        )
        return tuple(sorted(found, key=_order))


@dataclass(slots=True)
class _Municipality:
    uf: str
    codigo_municipio: str
    municipio: str
    sections: int = 0
    altered: int = 0
    contingencies: int = 0
    new_contingencies: int = 0


@dataclass(slots=True)
class _Quadro:
    cargos: dict[str, list[ProjecaoSecao]] = field(default_factory=dict)
    urns: dict[tuple[str, str, int, str], list[ProjecaoSecao]] = field(default_factory=dict)
    municipalities: dict[tuple[str, str], _Municipality] = field(default_factory=dict)
    altered_by_uf: dict[str, int] = field(default_factory=dict)
    machines: dict[tuple[str, str], int] = field(default_factory=dict)
    new_sections: list[ProjecaoSecao] = field(default_factory=list)

    def registrar_secao(self, secao: ProjecaoSecao) -> None:
        self._register_cargo(secao)
        self._register_urn(secao)
        self._register_section_counts(secao)
        self._register_machine(secao)
        if secao.status is StatusCorrespondencia.NOVA:
            self.new_sections.append(secao)

    def registrar_contingencia(self, item: ProjecaoContingencia) -> None:
        place = self._municipality(item.uf, item.codigo_municipio, item.municipio)
        place.contingencies += 1
        if item.status is StatusCorrespondencia.NOVA:
            place.new_contingencies += 1

    def _register_cargo(self, secao: ProjecaoSecao) -> None:
        if is_blank_token(secao.carga):
            return
        self.cargos.setdefault(secao.carga.strip(), []).append(secao)

    def _register_urn(self, secao: ProjecaoSecao) -> None:
        if is_blank_token(secao.urna):
            return
        key = (secao.uf, secao.codigo_municipio, secao.zona, secao.urna.strip())
        self.urns.setdefault(key, []).append(secao)

    def _register_section_counts(self, secao: ProjecaoSecao) -> None:
        place = self._municipality(secao.uf, secao.codigo_municipio, secao.municipio)
        place.sections += 1
        if secao.status is StatusCorrespondencia.ALTERADA:
            place.altered += 1

    def _register_machine(self, secao: ProjecaoSecao) -> None:
        if secao.status is not StatusCorrespondencia.ALTERADA:
            return
        self.altered_by_uf[secao.uf] = self.altered_by_uf.get(secao.uf, 0) + 1
        # Sentinels mean a blank machine name, same as the duplicate rules.
        if is_blank_token(secao.maquina_geracao):
            return
        key = (secao.uf, secao.maquina_geracao.strip())
        self.machines[key] = self.machines.get(key, 0) + 1

    def _municipality(self, uf: str, codigo: str, municipio: str) -> _Municipality:
        key = (uf, codigo)
        place = self.municipalities.get(key)
        if place is None:
            place = _Municipality(uf=uf, codigo_municipio=codigo, municipio=municipio)
            self.municipalities[key] = place
        return place


def _shared_cargos(quadro: _Quadro) -> tuple[Indicio, ...]:
    found: list[Indicio] = []
    for carga, group in quadro.cargos.items():
        if len(group) < 2:
            continue
        references = tuple(_section_reference(item) for item in group)
        uf, municipio = _scope(references)
        found.append(
            Indicio(
                codigo="CARGA_COMPARTILHADA",
                descricao=f"O código de carga {carga} está previsto em {len(group)} seções.",
                gravidade=Gravidade.ALTA,
                uf=uf,
                municipio=municipio,
                medida=f"Previsto em {len(group)} seções.",
                referencias=references,
            )
        )
    return tuple(found)


def _shared_urns(quadro: _Quadro) -> tuple[Indicio, ...]:
    found: list[Indicio] = []
    for (_uf, _codigo, zona, urna), group in quadro.urns.items():
        if len(group) < 2:
            continue
        references = tuple(_section_reference(item) for item in group)
        uf, municipio = _scope(references)
        found.append(
            Indicio(
                codigo="URNA_COMPARTILHADA_NA_ZONA",
                descricao=(
                    f"A urna {urna} está prevista em {len(group)} seções "
                    f"da zona {zona} de {municipio}."
                ),
                gravidade=Gravidade.ALTA,
                uf=uf,
                municipio=municipio,
                medida=f"Prevista em {len(group)} seções da zona {zona}.",
                referencias=references,
            )
        )
    return tuple(found)


def _atypical_alteration_rates(quadro: _Quadro) -> tuple[Indicio, ...]:
    return _rate_findings(
        quadro.municipalities.values(),
        events_of=lambda place: place.altered,
        size_of=lambda place: place.sections,
        build=_alteration_indicio,
    )


def _concentrated_new_contingencies(quadro: _Quadro) -> tuple[Indicio, ...]:
    return _rate_findings(
        quadro.municipalities.values(),
        events_of=lambda place: place.new_contingencies,
        size_of=lambda place: place.contingencies,
        build=_contingency_indicio,
    )


def _rate_findings(
    places: Iterable[_Municipality],
    events_of: Callable[[_Municipality], int],
    size_of: Callable[[_Municipality], int],
    build: Callable[[_Municipality, float], Indicio],
) -> tuple[Indicio, ...]:
    # Zeros are the ordinary case. They must not collapse the MAD to zero.
    population = [
        place for place in places if size_of(place) >= MIN_RATE_POPULATION and events_of(place) >= 1
    ]
    if len(population) < 2:
        return ()
    rates = [events_of(place) / size_of(place) for place in population]
    center = median(rates)
    spread = median_absolute_deviation(rates, center)
    if spread == 0:
        return ()
    found: list[Indicio] = []
    for place, rate in zip(population, rates, strict=True):
        events = events_of(place)
        if events < MIN_OUTLIER_EVENTS:
            continue
        score = modified_z(rate, center, spread)
        if score < MODIFIED_Z_THRESHOLD:
            continue
        found.append(build(place, score))
    return tuple(found)


def _alteration_indicio(place: _Municipality, score: float) -> Indicio:
    rate = place.altered / place.sections
    return Indicio(
        codigo="TAXA_ALTERACAO_ATIPICA",
        descricao=(
            f"{place.municipio} ({place.uf}) tem taxa de correspondência alterada "
            f"fora do padrão dos municípios: {rate:.2%} em {place.sections} seções "
            f"(z = {score:.1f})."
        ),
        gravidade=Gravidade.MEDIA,
        uf=place.uf,
        municipio=place.municipio,
        medida=f"{place.altered} seções alteradas em {place.sections}; z = {score:.1f}.",
        referencias=(),
    )


def _contingency_indicio(place: _Municipality, score: float) -> Indicio:
    return Indicio(
        codigo="CONTINGENCIA_NOVA_CONCENTRADA",
        descricao=(
            f"{place.municipio} ({place.uf}) concentrou {place.new_contingencies} "
            f"urnas de contingência novas em {place.contingencies} urnas "
            f"(z = {score:.1f})."
        ),
        gravidade=Gravidade.BAIXA,
        uf=place.uf,
        municipio=place.municipio,
        medida=(
            f"{place.new_contingencies} urnas novas em {place.contingencies}; z = {score:.1f}."
        ),
        referencias=(),
    )


def _concentrated_machines(quadro: _Quadro) -> tuple[Indicio, ...]:
    found: list[Indicio] = []
    for (uf, machine), count in quadro.machines.items():
        total = quadro.altered_by_uf[uf]
        if total < MIN_ALTERED_SECTIONS_IN_UF:
            continue
        if count < MIN_MACHINE_ALTERED_SECTIONS:
            continue
        if count / total < MIN_MACHINE_SHARE:
            continue
        found.append(
            Indicio(
                codigo="MAQUINA_CONCENTRA_ALTERACOES",
                descricao=(
                    f"Em {uf}, a máquina {machine} gerou {count} das {total} "
                    "correspondências alteradas."
                ),
                gravidade=Gravidade.MEDIA,
                uf=uf,
                municipio="",
                medida=f"{count} de {total} correspondências alteradas.",
                referencias=(),
            )
        )
    return tuple(found)


def _new_sections(quadro: _Quadro) -> tuple[Indicio, ...]:
    return tuple(_new_section(secao) for secao in quadro.new_sections)


def _new_section(secao: ProjecaoSecao) -> Indicio:
    return Indicio(
        codigo="SECAO_NOVA",
        descricao=(
            f"A seção {secao.secao} de {secao.municipio} ({secao.uf}), zona {secao.zona}, "
            "entrou como correspondência nova entre as gerações."
        ),
        gravidade=Gravidade.MEDIA,
        uf=secao.uf,
        municipio=secao.municipio,
        medida=f"Seção {secao.secao}, zona {secao.zona}.",
        referencias=(_section_reference(secao),),
    )


def _section_reference(secao: ProjecaoSecao) -> Referencia:
    return Referencia(
        uf=secao.uf,
        codigo_municipio=secao.codigo_municipio,
        municipio=secao.municipio,
        zona=secao.zona,
        secao=secao.secao,
        urna=secao.urna,
    )


def _scope(references: tuple[Referencia, ...]) -> tuple[str, str]:
    places = {(item.uf, item.codigo_municipio) for item in references}
    if len(places) != 1:
        return "", ""
    return references[0].uf, references[0].municipio


def _order(indicio: Indicio) -> tuple[int, str, str, str, str]:
    return (
        _GRAVITY_ORDER[indicio.gravidade],
        indicio.codigo,
        indicio.uf,
        indicio.municipio,
        indicio.descricao,
    )
