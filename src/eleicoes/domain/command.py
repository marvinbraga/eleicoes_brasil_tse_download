from dataclasses import dataclass
from pathlib import Path

from eleicoes.domain.values import DiscoveryRequest


@dataclass(frozen=True, slots=True)
class DownloadCommand:
    request: DiscoveryRequest
    destination: Path
