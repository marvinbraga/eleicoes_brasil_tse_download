from eleicoes.adapters.ckan_municipal_catalog import CkanMunicipalCatalog
from eleicoes.domain.values import (
    DiscoveryRequest,
    ElectionYear,
    RemoteZip,
    default_turnos,
    default_ufs,
)
from eleicoes.ports.ckan import CkanPackage, CkanPage

_CDN = "https://cdn.tse.jus.br/estatistica/sead/odsele"


class _Gateway:
    def __init__(self, packages: dict[str, CkanPackage]) -> None:
        self.packages = packages
        self.shown: list[str] = []

    def package_show(self, package_id: str) -> CkanPackage | None:
        self.shown.append(package_id)
        return self.packages.get(package_id)

    def package_search(self, query: str, *, start: int, rows: int) -> CkanPage:
        del query, start, rows
        raise AssertionError("search must not be used")


def _zip(folder: str, name: str) -> RemoteZip:
    return RemoteZip(url=f"{_CDN}/{folder}/{name}", filename=name)


def _request() -> DiscoveryRequest:
    return DiscoveryRequest(ElectionYear(2024), default_turnos(), default_ufs())


def test_only_the_allow_listed_zips_are_returned() -> None:
    gateway = _Gateway(
        {
            "candidatos-2024": CkanPackage(
                "candidatos-2024",
                ("candidatos",),
                (
                    _zip("consulta_cand", "consulta_cand_2024.zip"),
                    _zip("bem_candidato", "bem_candidato_2024.zip"),
                    _zip("fotos", "foto_cand2024_AC_div.zip"),
                    _zip("consulta_vagas", "consulta_vagas_2024.zip"),
                ),
            ),
            "resultados-2024": CkanPackage(
                "resultados-2024",
                ("resultados",),
                (_zip("detalhe_votacao_munzona", "detalhe_votacao_munzona_2024.zip"),),
            ),
        }
    )
    found = CkanMunicipalCatalog(gateway).discover(_request())
    assert [item.filename for item in found] == [
        "consulta_cand_2024.zip",
        "consulta_vagas_2024.zip",
        "detalhe_votacao_munzona_2024.zip",
    ]
    assert gateway.shown == ["candidatos-2024", "resultados-2024"]


def test_missing_package_returns_what_exists() -> None:
    gateway = _Gateway({})
    assert CkanMunicipalCatalog(gateway).discover(_request()) == ()
