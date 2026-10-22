"""Lê os pacotes candidatos-{ano} e resultados-{ano} e devolve só os zips da lista fechada."""

from eleicoes.domain.municipal_contract import municipal_archives
from eleicoes.domain.values import DiscoveryRequest, RemoteZip
from eleicoes.ports.ckan import CkanGateway, CkanPackage


class CkanMunicipalCatalog:
    def __init__(self, gateway: CkanGateway) -> None:
        self._gateway = gateway

    def discover(self, request: DiscoveryRequest) -> tuple[RemoteZip, ...]:
        wanted = municipal_archives(request.year)
        packages: dict[str, CkanPackage | None] = {}
        found: list[RemoteZip] = []
        for item in wanted:
            if item.package not in packages:
                packages[item.package] = self._gateway.package_show(item.package)
            package = packages[item.package]
            if package is None:
                continue
            match = next(
                (zip_ for zip_ in package.archives if zip_.filename == item.filename), None
            )
            if match is not None:
                found.append(match)
        return tuple(found)
