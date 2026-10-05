import json
from pathlib import Path
from urllib.parse import quote

from tests.support import FakeHttp

from eleicoes.composition.command_builder import DownloadCommandBuilder
from eleicoes.composition.wiring import build_app
from eleicoes.domain.report import EXIT_NOT_PUBLISHED, EXIT_SUCCESS
from eleicoes.domain.values import ElectionYear

API = "https://dadosabertos.tse.jus.br/api/3/action/"


def test_wiring_downloads_ckan_zips_when_totalizacao_is_absent(tmp_path: Path) -> None:
    package_id = "resultados-2026-arquivos-transmitidos-para-totalizacao"
    show_url = f"{API}package_show?id={quote(package_id, safe='')}"
    query = "groups:resultados AND name:*2026*"
    search_url = f"{API}package_search?fq={quote(query, safe='')}&start=0&rows=100"
    zip_url = "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/logsgedai/log.zip"
    body = {
        "success": True,
        "result": {
            "count": 2,
            "results": [
                {
                    "name": "resultados-2026-logs-gedai-1-turno",
                    "groups": [{"name": "resultados"}],
                    "resources": [
                        {"url": zip_url},
                        {"url": zip_url + ".sha512"},
                    ],
                },
                {
                    "name": "perfil-2026",
                    "groups": [{"name": "eleitorado"}],
                    "resources": [{"url": "https://cdn.tse.jus.br/perfil.zip"}],
                },
            ],
        },
    }
    http = FakeHttp(
        {
            show_url: (404, b'{"success": false}'),
            search_url: (200, json.dumps(body).encode()),
            zip_url: (200, b"PK\x03\x04"),
        }
    )
    command = (
        DownloadCommandBuilder().with_year(ElectionYear(2026)).with_destination(tmp_path).build()
    )
    report = build_app(http).execute(command)
    assert report.exit_code == EXIT_SUCCESS
    assert report.discovered == 1
    assert report.downloaded == 1
    assert (tmp_path / "outros" / "log.zip").read_bytes().startswith(b"PK")
    assert "https://cdn.tse.jus.br/perfil.zip" not in http.urls
    assert zip_url + ".sha512" not in http.urls


def test_wiring_prefers_classic_names_when_the_package_exists(tmp_path: Path) -> None:
    package_id = "resultados-2022-arquivos-transmitidos-para-totalizacao"
    show_url = f"{API}package_show?id={quote(package_id, safe='')}"
    body = {
        "success": True,
        "result": {
            "name": package_id,
            "groups": [{"name": "resultados"}],
            "resources": [{"url": "https://cdn.tse.jus.br/nao-usar.zip"}],
        },
    }
    http = FakeHttp({show_url: (200, json.dumps(body).encode())}, default=(200, b"PK"))
    command = (
        DownloadCommandBuilder().with_year(ElectionYear(2022)).with_destination(tmp_path).build()
    )
    report = build_app(http).execute(command)
    assert report.discovered == 56
    assert report.downloaded == 56
    assert report.missing == 0
    assert "https://cdn.tse.jus.br/nao-usar.zip" not in http.urls
    assert any(url.endswith("bu_imgbu_logjez_rdv_vscmr_2022_2t_ZZ.zip") for url in http.urls)


def test_wiring_reports_nothing_published(tmp_path: Path) -> None:
    package_id = "resultados-2030-arquivos-transmitidos-para-totalizacao"
    show_url = f"{API}package_show?id={quote(package_id, safe='')}"
    query = "groups:resultados AND name:*2030*"
    search_url = f"{API}package_search?fq={quote(query, safe='')}&start=0&rows=100"
    http = FakeHttp(
        {
            show_url: (404, b'{"success": false}'),
            search_url: (200, b'{"success": true, "result": {"count": 0, "results": []}}'),
        }
    )
    command = (
        DownloadCommandBuilder().with_year(ElectionYear(2030)).with_destination(tmp_path).build()
    )
    report = build_app(http).execute(command)
    assert report.exit_code == EXIT_NOT_PUBLISHED
    assert list(tmp_path.iterdir()) == []
