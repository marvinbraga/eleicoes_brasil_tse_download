from pathlib import Path

from eleicoes.domain.command import DownloadCommand
from eleicoes.domain.errors import MissingElectionYearError
from eleicoes.domain.values import DiscoveryRequest, ElectionYear, default_turnos, default_ufs


class DownloadCommandBuilder:
    """Monta o pedido de download a partir do ano e dos overrides opcionais."""

    def __init__(self) -> None:
        self._year: ElectionYear | None = None
        self._cdn_directory: str | None = None
        self._dataset_ref: str | None = None
        self._destination: Path | None = None

    def with_year(self, year: ElectionYear) -> "DownloadCommandBuilder":
        self._year = year
        return self

    def with_cdn_directory(self, directory: str | None) -> "DownloadCommandBuilder":
        self._cdn_directory = directory
        return self

    def with_dataset_ref(self, dataset_ref: str | None) -> "DownloadCommandBuilder":
        self._dataset_ref = dataset_ref
        return self

    def with_destination(self, destination: Path | None) -> "DownloadCommandBuilder":
        self._destination = destination
        return self

    def build(self) -> DownloadCommand:
        if self._year is None:
            raise MissingElectionYearError()
        year = self._year
        destination = self._destination
        if destination is None:
            destination = Path("downloads") / str(year.value)
        return DownloadCommand(
            request=DiscoveryRequest(
                year=year,
                turnos=default_turnos(),
                ufs=default_ufs(),
                cdn_directory=self._cdn_directory,
                dataset_ref=self._dataset_ref,
            ),
            destination=destination,
        )
