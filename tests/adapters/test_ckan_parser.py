import json

import pytest

from eleicoes.adapters.ckan_parser import (
    _as_mapping,
    package_from_mapping,
    parse_package_search,
    parse_package_show,
)
from eleicoes.domain.errors import CkanPayloadError
from eleicoes.ports.ckan import CkanPage

ZIP_URL = (
    "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/logsgedai/log_gedai_1t_AC.zip"
)
SECOND_ZIP = (
    "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/correspesp/CESP_1t_AC.ZIP"
)
SHA_URL = ZIP_URL + ".sha512"
CSV_URL = "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/not-a-zip.csv"

PACKAGE_SHOW = {
    "success": True,
    "result": {
        "name": "resultados-2026-logs-do-sistema-gedai-1-turno",
        "groups": [{"name": "resultados"}, "ignorado", {"title": "sem nome"}],
        "resources": [
            {"url": ZIP_URL, "format": "ZIP"},
            {"url": SHA_URL, "format": ""},
            {"url": CSV_URL, "format": "CSV"},
            {"url": SECOND_ZIP, "format": "CSV"},
            {"url": ZIP_URL, "format": "ZIP"},
            {"name": "sem url"},
            "quebrado",
            {"url": "ftp://cdn.tse.jus.br/file.zip"},
        ],
    },
}

PACKAGE_SEARCH = {
    "success": True,
    "result": {
        "count": 2,
        "results": [
            PACKAGE_SHOW["result"],
            {
                "name": "perfil-do-eleitorado-2026",
                "groups": [{"name": "eleitorado"}],
                "resources": [{"url": "https://cdn.tse.jus.br/eleitorado/perfil_2026.zip"}],
            },
        ],
    },
}


def test_package_show_fixture_keeps_only_real_zips() -> None:
    package = parse_package_show(json.dumps(PACKAGE_SHOW))
    assert package is not None
    assert [item.filename for item in package.archives] == [
        "log_gedai_1t_AC.zip",
        "CESP_1t_AC.ZIP",
    ]
    assert package.groups == ("resultados",)


def test_package_search_fixture_parses_every_result() -> None:
    page = parse_package_search(json.dumps(PACKAGE_SEARCH))
    assert page.total == 2
    assert [package.name for package in page.packages] == [
        "resultados-2026-logs-do-sistema-gedai-1-turno",
        "perfil-do-eleitorado-2026",
    ]
    assert page.packages[1].archives[0].filename == "perfil_2026.zip"


def test_package_show_not_found_payload_is_absent() -> None:
    raw = json.dumps({"success": False, "error": {"message": "Não encontrado"}})
    assert parse_package_show(raw) is None


@pytest.mark.parametrize(
    "raw",
    [
        "não é json",
        "[]",
        json.dumps({"success": True}),
        json.dumps({"result": {}}),
        json.dumps({"success": True, "result": {"groups": [], "resources": []}}),
        json.dumps({"success": True, "result": {"name": "ok", "groups": "não", "resources": []}}),
        json.dumps({"success": True, "result": {"name": "ok", "groups": None, "resources": "não"}}),
    ],
)
def test_package_show_rejects_malformed_payloads(raw: str) -> None:
    with pytest.raises(CkanPayloadError):
        parse_package_show(raw)


def test_package_search_rejects_failed_or_incomplete_payload() -> None:
    with pytest.raises(CkanPayloadError):
        parse_package_search(json.dumps({"success": False}))
    with pytest.raises(CkanPayloadError):
        parse_package_search(
            json.dumps({"success": True, "result": {"count": True, "results": []}})
        )
    with pytest.raises(CkanPayloadError):
        parse_package_search(json.dumps({"success": True, "result": {"count": 0, "results": {}}}))


def test_negative_page_total_is_rejected() -> None:
    with pytest.raises(CkanPayloadError):
        CkanPage(total=-1, packages=())


def test_mapping_with_non_string_key_is_rejected() -> None:
    with pytest.raises(CkanPayloadError):
        _as_mapping({1: "x"})


def test_package_without_resources_has_no_archives() -> None:
    package = package_from_mapping(
        {"name": "resultados-2026-vazio", "groups": None, "resources": None}
    )
    assert package.archives == ()
    assert package.groups == ()
