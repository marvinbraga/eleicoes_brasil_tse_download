import json

from tests.adapters.test_ckan_parser import PACKAGE_SEARCH
from tests.support import MemoryGateway, national_request, zip_at

from eleicoes.adapters.ckan_catalog import (
    CkanExplicitCatalog,
    CkanTotalizacaoProbe,
    CkanYearCatalog,
)
from eleicoes.adapters.ckan_parser import parse_package_search
from eleicoes.ports.ckan import CkanPackage, CkanPage


def test_absent_classic_package_uses_the_broader_search_fixture() -> None:
    page = parse_package_search(json.dumps(PACKAGE_SEARCH))
    gateway = MemoryGateway(pages=(page,))
    found = CkanYearCatalog(gateway).discover(national_request(2026))
    assert [item.filename for item in found] == ["log_gedai_1t_AC.zip", "CESP_1t_AC.ZIP"]
    assert "perfil_2026.zip" not in {item.filename for item in found}
    assert gateway.searches[0][0] == "groups:resultados AND name:*2026*"


def test_year_catalog_pages_until_the_total_is_consumed() -> None:
    first = CkanPackage(
        "resultados-2026-a",
        ("resultados",),
        (zip_at("https://cdn.example/a.zip"),),
    )
    unrelated = CkanPackage(
        "resultados-20260-b",
        ("resultados",),
        (zip_at("https://cdn.example/b.zip"),),
    )
    other_group = CkanPackage(
        "resultados-2026-c",
        ("eleitorado",),
        (zip_at("https://cdn.example/c.zip"),),
    )
    second = CkanPackage(
        "resultados-2026-d",
        ("resultados",),
        (zip_at("https://cdn.example/a.zip"), zip_at("https://cdn.example/d.zip")),
    )
    gateway = MemoryGateway(
        pages=(
            CkanPage(total=4, packages=(first, unrelated, other_group)),
            CkanPage(total=4, packages=(second,)),
        )
    )
    found = CkanYearCatalog(gateway).discover(national_request(2026))
    assert [item.filename for item in found] == ["a.zip", "d.zip"]
    assert [call[1] for call in gateway.searches] == [0, 3]


def test_explicit_dataset_url_returns_only_that_package() -> None:
    package = CkanPackage("meu-pacote", ("resultados",), (zip_at("https://cdn.example/only.zip"),))
    gateway = MemoryGateway(shown={"meu-pacote": package})
    request = national_request(
        2026,
        dataset_ref="https://dadosabertos.tse.jus.br/dataset/meu-pacote/",
    )
    found = CkanExplicitCatalog(gateway).discover(request)
    assert [item.filename for item in found] == ["only.zip"]
    assert gateway.shown_ids == ["meu-pacote"]


def test_missing_explicit_package_is_an_empty_catalog() -> None:
    gateway = MemoryGateway(shown={"ausente": None})
    found = CkanExplicitCatalog(gateway).discover(national_request(2026, dataset_ref="ausente"))
    assert found == ()


def test_explicit_catalog_without_ref_is_empty() -> None:
    assert CkanExplicitCatalog(MemoryGateway()).discover(national_request(2026)) == ()


def test_probe_checks_the_totalizacao_package_id() -> None:
    package_id = "resultados-2022-arquivos-transmitidos-para-totalizacao"
    present = CkanPackage(package_id, ("resultados",), ())
    gateway = MemoryGateway(shown={package_id: present})
    assert CkanTotalizacaoProbe(gateway).is_published(national_request(2022).year) is True
    missing = MemoryGateway(shown={})
    assert CkanTotalizacaoProbe(missing).is_published(national_request(2026).year) is False
    assert missing.shown_ids == ["resultados-2026-arquivos-transmitidos-para-totalizacao"]
