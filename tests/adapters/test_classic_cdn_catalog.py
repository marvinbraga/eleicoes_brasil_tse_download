from tests.support import national_request

from eleicoes.adapters.classic_cdn_catalog import ClassicCdnCatalog
from eleicoes.domain.values import UF_CODES, DiscoveryRequest, ElectionYear, Turno, default_ufs


def test_classic_catalog_builds_both_turns_and_every_uf() -> None:
    files = ClassicCdnCatalog().discover(national_request(2022))
    assert len(files) == len(UF_CODES) * 2
    expected = {
        f"bu_imgbu_logjez_rdv_vscmr_2022_{turno}t_{uf}.zip" for turno in (1, 2) for uf in UF_CODES
    }
    assert {item.filename for item in files} == expected
    sample = next(item for item in files if item.filename.endswith("_1t_AC.zip"))
    prefix = "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2022/arqurnatot/"
    assert sample.url == prefix + sample.filename


def test_classic_catalog_uses_cdn_override_without_double_slash() -> None:
    request = national_request(2024, cdn_directory="https://cdn.example/base/")
    files = ClassicCdnCatalog().discover(request)
    assert files[0].url.startswith("https://cdn.example/base/bu_imgbu_logjez_rdv_vscmr_2024_")
    assert "base//" not in files[0].url


def test_classic_catalog_honors_a_single_turn() -> None:
    request = DiscoveryRequest(
        year=ElectionYear(2024),
        turnos=(Turno(1),),
        ufs=default_ufs(),
    )
    files = ClassicCdnCatalog().discover(request)
    assert len(files) == len(UF_CODES)
    assert all("_1t_" in item.filename for item in files)
    assert all("_2t_" not in item.filename for item in files)
