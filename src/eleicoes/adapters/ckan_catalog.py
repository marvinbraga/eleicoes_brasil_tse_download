import re
from collections.abc import Iterable
from typing import Final

from eleicoes.domain.values import DiscoveryRequest, ElectionYear, PackageRef, RemoteZip
from eleicoes.ports.ckan import CkanGateway, CkanPackage

PAGE_ROWS: Final = 100
_MAX_START: Final = 5_000
RESULTADOS_GROUP: Final = "resultados"
TOTALIZACAO_PACKAGE: Final = "resultados-{year}-arquivos-transmitidos-para-totalizacao"


class CkanTotalizacaoProbe:
    def __init__(self, gateway: CkanGateway) -> None:
        self._gateway = gateway

    def is_published(self, year: ElectionYear) -> bool:
        package_id = TOTALIZACAO_PACKAGE.format(year=year.value)
        return self._gateway.package_show(package_id) is not None


class CkanYearCatalog:
    """Lista zips dos datasets do grupo resultados cujo nome contém o ano."""

    def __init__(self, gateway: CkanGateway) -> None:
        self._gateway = gateway

    def discover(self, request: DiscoveryRequest) -> tuple[RemoteZip, ...]:
        selected = [
            package
            for package in self._collect(request.year)
            if _belongs_to_year(package, request.year)
        ]
        archives = [archive for package in selected for archive in package.archives]
        return _unique(archives)

    def _collect(self, year: ElectionYear) -> tuple[CkanPackage, ...]:
        query = f"groups:{RESULTADOS_GROUP} AND name:*{year.value}*"
        collected: list[CkanPackage] = []
        start = 0
        while start <= _MAX_START:
            page = self._gateway.package_search(query, start=start, rows=PAGE_ROWS)
            collected.extend(page.packages)
            start += len(page.packages)
            if not page.packages or start >= page.total:
                break
        return tuple(collected)


class CkanExplicitCatalog:
    """Lê um único pacote indicado por id ou pela URL da página de dados abertos."""

    def __init__(self, gateway: CkanGateway) -> None:
        self._gateway = gateway

    def discover(self, request: DiscoveryRequest) -> tuple[RemoteZip, ...]:
        if request.dataset_ref is None:
            return ()
        package_id = PackageRef.parse(request.dataset_ref).package_id
        package = self._gateway.package_show(package_id)
        if package is None:
            return ()
        return _unique(package.archives)


def _belongs_to_year(package: CkanPackage, year: ElectionYear) -> bool:
    if RESULTADOS_GROUP not in package.groups:
        return False
    return re.search(rf"(^|[^0-9]){year.value}([^0-9]|$)", package.name) is not None


def _unique(archives: Iterable[RemoteZip]) -> tuple[RemoteZip, ...]:
    seen: set[str] = set()
    unique: list[RemoteZip] = []
    for archive in archives:
        if archive.url in seen:
            continue
        seen.add(archive.url)
        unique.append(archive)
    return tuple(unique)
