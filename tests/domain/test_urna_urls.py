from eleicoes.domain.urna_models import (
    MunicipioCode,
    PleitoCode,
    SecaoCode,
    UrnaAddress,
    UrnaTemplates,
    ZonaCode,
)
from eleicoes.domain.urna_urls import UrnaUrlBuilder
from eleicoes.domain.values import Uf

HASH = "65312d4970434764763677645275443244505641544f4678695966744b623941565a665876706c6d7271343d"
BU = "o03220ac0139200010003-bu.dat"
AUX_URL = (
    "https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3220/dados/"
    "ac/01392/0001/0003/p003220-ac-m01392-z0001-s0003-aux.json"
)
FILE_URL = (
    "https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3220/dados/"
    f"ac/01392/0001/0003/{HASH}/{BU}"
)
INDEX_URL = (
    "https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3220/config/ac/ac-p003220-cs.json"
)
SECTION_TEMPLATE = "<base>/<ambiente>/<ciclo>/arquivo-urna/<cd_pleito>/config/<uf>"
AUX_TEMPLATE = (
    "<base>/<ambiente>/<ciclo>/arquivo-urna/<cd_pleito>/dados/<uf>/<municipio>/<zona>/<secao>"
)


def _builder() -> UrnaUrlBuilder:
    templates = UrnaTemplates(SECTION_TEMPLATE, AUX_TEMPLATE)
    return UrnaUrlBuilder(templates, "ele2026", PleitoCode("3220"))


def _rio(*, municipio: str, zona: str, secao: str) -> UrnaAddress:
    return UrnaAddress(
        uf=Uf("AC"),
        municipio=MunicipioCode(municipio),
        zona=ZonaCode(zona),
        secao=SecaoCode(secao),
    )


def test_builder_emits_the_rio_branco_auxiliary_and_bu_urls() -> None:
    address = _rio(municipio="01392", zona="0001", secao="0003")
    builder = _builder()
    assert builder.section_index(Uf("AC")) == INDEX_URL
    assert builder.auxiliary(address) == AUX_URL
    assert builder.file(address, HASH, BU) == FILE_URL


def test_leading_zeros_are_kept_and_short_codes_are_padded() -> None:
    padded = _rio(municipio="01392", zona="0001", secao="0003")
    short = _rio(municipio="1392", zona="1", secao="3")
    assert padded.municipio.value == "01392"
    assert padded.zona.value == "0001"
    assert padded.secao.value == "0003"
    assert short.municipio.value == "01392"
    assert short.zona.value == "0001"
    assert short.secao.value == "0003"
    assert _builder().auxiliary(short) == AUX_URL
    assert _builder().file(short, HASH, BU) == FILE_URL
