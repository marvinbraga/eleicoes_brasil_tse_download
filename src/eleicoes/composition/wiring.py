from eleicoes.adapters.ckan_catalog import (
    CkanExplicitCatalog,
    CkanTotalizacaoProbe,
    CkanYearCatalog,
)
from eleicoes.adapters.ckan_http import RequestsCkanGateway
from eleicoes.adapters.classic_cdn_catalog import ClassicCdnCatalog
from eleicoes.adapters.requests_http import RequestsHttpClient
from eleicoes.adapters.streaming_transfer import StreamingFileTransfer
from eleicoes.ports.http import HttpClient
from eleicoes.use_cases.download_election import DownloadElectionArchives


def build_app(http: HttpClient | None = None) -> DownloadElectionArchives:
    client = http if http is not None else RequestsHttpClient()
    gateway = RequestsCkanGateway(client)
    return DownloadElectionArchives(
        publication=CkanTotalizacaoProbe(gateway),
        classic_catalog=ClassicCdnCatalog(),
        year_catalog=CkanYearCatalog(gateway),
        dataset_catalog=CkanExplicitCatalog(gateway),
        transfer=StreamingFileTransfer(client),
    )
