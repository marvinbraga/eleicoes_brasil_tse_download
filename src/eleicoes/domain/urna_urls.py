"""Literal substitution of the divulgação arquivo-urna templates."""

from typing import Final

from eleicoes.domain.errors import InvalidUrnaCodeError
from eleicoes.domain.urna_models import PleitoCode, UrnaAddress, UrnaTemplates, _require_leaf
from eleicoes.domain.values import Uf

RESULTADOS_ORIGIN: Final = "https://resultados.tse.jus.br"
OFFICIAL_ENVIRONMENT: Final = "oficial"
CONFIG_URL: Final = f"{RESULTADOS_ORIGIN}/oficial/comum/config/ele-c.json"


class UrnaUrlBuilder:
    """Fills `<base>`, `<ambiente>`, `<ciclo>`, `<cd_pleito>` and the section placeholders."""

    def __init__(self, templates: UrnaTemplates, ciclo: str, pleito: PleitoCode) -> None:
        if not ciclo:
            raise InvalidUrnaCodeError(ciclo)
        self._templates = templates
        self._ciclo = ciclo
        self._pleito = pleito

    def section_index(self, uf: Uf) -> str:
        root = self._fill(self._templates.section_config, uf, None)
        code = uf.code.lower()
        return f"{root}/{code}-p{self._pleito.filename_digits}-cs.json"

    def auxiliary(self, address: UrnaAddress) -> str:
        root = self._fill(self._templates.auxiliary, address.uf, address)
        return f"{root}/{_auxiliary_name(self._pleito, address)}"

    def file(self, address: UrnaAddress, digest: str, filename: str) -> str:
        _require_leaf(digest)
        _require_leaf(filename)
        root = self._fill(self._templates.auxiliary, address.uf, address)
        return f"{root}/{digest}/{filename}"

    def _fill(self, template: str, uf: Uf, address: UrnaAddress | None) -> str:
        municipio = "" if address is None else address.municipio.value
        zona = "" if address is None else address.zona.value
        secao = "" if address is None else address.secao.value
        return (
            template.replace("<base>", RESULTADOS_ORIGIN)
            .replace("<ambiente>", OFFICIAL_ENVIRONMENT)
            .replace("<ciclo>", self._ciclo)
            .replace("<cd_pleito>", self._pleito.value)
            .replace("<uf>", uf.code.lower())
            .replace("<municipio>", municipio)
            .replace("<zona>", zona)
            .replace("<secao>", secao)
        )


def _auxiliary_name(pleito: PleitoCode, address: UrnaAddress) -> str:
    uf = address.uf.code.lower()
    return (
        f"p{pleito.filename_digits}-{uf}-m{address.municipio.value}"
        f"-z{address.zona.value}-s{address.secao.value}-aux.json"
    )
