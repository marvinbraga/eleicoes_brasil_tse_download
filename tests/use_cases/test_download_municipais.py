from pathlib import Path

from eleicoes.domain.command import DownloadCommand
from eleicoes.domain.report import TransferStatus
from eleicoes.domain.values import (
    DiscoveryRequest,
    ElectionYear,
    RemoteZip,
    default_turnos,
    default_ufs,
)
from eleicoes.use_cases.download_municipais import DownloadMunicipalArchives


class _Catalog:
    def discover(self, request: DiscoveryRequest) -> tuple[RemoteZip, ...]:
        del request
        return (
            RemoteZip("https://cdn.tse.jus.br/x/consulta_cand_2024.zip", "consulta_cand_2024.zip"),
        )


class _Transfer:
    def __init__(self) -> None:
        self.names: list[str] = []

    def transfer(self, archive: RemoteZip, destination: Path) -> TransferStatus:
        del destination
        self.names.append(archive.filename)
        return TransferStatus.DOWNLOADED


def test_missing_catalog_entries_become_ausente(tmp_path: Path) -> None:
    transfer = _Transfer()
    command = DownloadCommand(
        DiscoveryRequest(ElectionYear(2024), default_turnos(), default_ufs()), tmp_path
    )
    report = DownloadMunicipalArchives(_Catalog(), transfer).execute(command)
    assert transfer.names == ["consulta_cand_2024.zip"]
    assert [(item.filename, item.status) for item in report.outcomes] == [
        ("consulta_cand_2024.zip", TransferStatus.DOWNLOADED),
        ("consulta_vagas_2024.zip", TransferStatus.MISSING),
        ("detalhe_votacao_munzona_2024.zip", TransferStatus.MISSING),
    ]
