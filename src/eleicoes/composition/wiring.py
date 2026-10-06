from collections.abc import Mapping

from eleicoes.adapters.asn1.boletim_reader import Asn1BoletimReader
from eleicoes.adapters.ckan_catalog import (
    CkanExplicitCatalog,
    CkanTotalizacaoProbe,
    CkanYearCatalog,
)
from eleicoes.adapters.ckan_http import RequestsCkanGateway
from eleicoes.adapters.classic_cdn_catalog import ClassicCdnCatalog
from eleicoes.adapters.csv_index_reader import CsvIndexReader
from eleicoes.adapters.postgres_boletim import PostgresBoletimSink
from eleicoes.adapters.postgres_sink import PostgresTabularSink, connect_postgres
from eleicoes.adapters.requests_http import RequestsHttpClient
from eleicoes.adapters.streaming_transfer import StreamingFileTransfer
from eleicoes.adapters.system_time import BlockingSleeper, MonotonicClock
from eleicoes.adapters.urna_index import CsvUrnaLedger
from eleicoes.adapters.urna_json import UrnaJsonReader
from eleicoes.adapters.urna_store import PartialUrnaStore
from eleicoes.adapters.zip_archive_reader import ZipArchiveReader
from eleicoes.composition.correspondencia import _host_settings
from eleicoes.domain.request_pace import RequestPace
from eleicoes.ports.http import HttpClient
from eleicoes.use_cases.download_election import DownloadElectionArchives
from eleicoes.use_cases.download_urnas import DownloadUrnaFiles
from eleicoes.use_cases.import_boletins import ImportBoletins
from eleicoes.use_cases.import_election import ImportElectionTables


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


def build_urna_download(http: HttpClient | None = None) -> DownloadUrnaFiles:
    client = http if http is not None else RequestsHttpClient()
    sleeper = BlockingSleeper()
    return DownloadUrnaFiles(
        http=client,
        pace=RequestPace(MonotonicClock(), sleeper),
        documents=UrnaJsonReader(),
        store=PartialUrnaStore(),
        ledger=CsvUrnaLedger(),
        sleeper=sleeper,
    )


def build_import(env: Mapping[str, str]) -> ImportElectionTables:
    return ImportElectionTables(
        index=CsvIndexReader(),
        archives=ZipArchiveReader(),
        sink=PostgresTabularSink(lambda: connect_postgres(env)),
    )


def build_boletim_import(env: Mapping[str, str]) -> ImportBoletins:
    settings = _host_settings(env)
    return ImportBoletins(
        reader=Asn1BoletimReader(),
        sink=PostgresBoletimSink(lambda: connect_postgres(settings)),
    )
