import json
from urllib.parse import quote

import pytest
from tests.support import FakeHttp

from eleicoes.adapters.ckan_http import RequestsCkanGateway
from eleicoes.domain.errors import CkanPayloadError, UnexpectedHttpStatusError

API = "https://dadosabertos.tse.jus.br/api/3/action/"


def _show_url(package_id: str) -> str:
    return f"{API}package_show?id={quote(package_id, safe='')}"


def test_package_show_404_is_absent_and_body_is_not_a_package() -> None:
    package_id = "resultados-2026-arquivos-transmitidos-para-totalizacao"
    http = FakeHttp({_show_url(package_id): (404, b'{"success": false}')})
    assert RequestsCkanGateway(http).package_show(package_id) is None
    assert http.responses[0].body.closed is True


def test_package_show_200_reads_the_json_body() -> None:
    package_id = "resultados-2022-arquivos-transmitidos-para-totalizacao"
    payload = {
        "success": True,
        "result": {
            "name": package_id,
            "groups": [{"name": "resultados"}],
            "resources": [{"url": "https://cdn.tse.jus.br/arquivo.zip"}],
        },
    }
    http = FakeHttp({_show_url(package_id): (200, json.dumps(payload).encode())})
    package = RequestsCkanGateway(http).package_show(package_id)
    assert package is not None
    assert package.archives[0].filename == "arquivo.zip"
    assert http.responses[0].body.reads == 1


def test_package_show_success_false_on_http_200_is_absent() -> None:
    package_id = "ausente"
    http = FakeHttp({_show_url(package_id): (200, b'{"success": false}')})
    assert RequestsCkanGateway(http).package_show(package_id) is None


def test_unexpected_status_and_invalid_bytes_fail() -> None:
    gateway = RequestsCkanGateway(FakeHttp({_show_url("x"): (500, b"erro")}))
    with pytest.raises(UnexpectedHttpStatusError):
        gateway.package_show("x")
    broken = RequestsCkanGateway(FakeHttp({_show_url("y"): (200, b"\xff")}))
    with pytest.raises(CkanPayloadError):
        broken.package_show("y")


def test_package_search_builds_the_fq_query() -> None:
    query = "groups:resultados AND name:*2026*"
    url = f"{API}package_search?fq={quote(query, safe='')}&start=0&rows=100"
    payload = {"success": True, "result": {"count": 0, "results": []}}
    http = FakeHttp({url: (200, json.dumps(payload).encode())})
    page = RequestsCkanGateway(http).package_search(query, start=0, rows=100)
    assert page.total == 0
    assert page.packages == ()
    assert http.urls == [url]


def test_package_search_rejects_an_unexpected_status() -> None:
    query = "groups:resultados AND name:*2026*"
    url = f"{API}package_search?fq={quote(query, safe='')}&start=0&rows=100"
    gateway = RequestsCkanGateway(FakeHttp({url: (503, b"indisponivel")}))
    with pytest.raises(UnexpectedHttpStatusError):
        gateway.package_search(query, start=0, rows=100)


def test_api_base_without_slash_is_normalized() -> None:
    gateway = RequestsCkanGateway(FakeHttp(), api_base="https://ckan.example/api/3/action")
    assert gateway._api_base.endswith("/")
