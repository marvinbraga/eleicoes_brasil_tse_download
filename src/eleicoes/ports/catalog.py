from typing import Protocol

from eleicoes.domain.values import DiscoveryRequest, RemoteZip


class Catalog(Protocol):
    def discover(self, request: DiscoveryRequest) -> tuple[RemoteZip, ...]: ...
