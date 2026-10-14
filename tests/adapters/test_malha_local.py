import base64
import json
from pathlib import Path

import pytest

from eleicoes.adapters.malha_local import LocalMeshAssets
from eleicoes.domain.mapa import MarkInvalidError, MeshMissingError

_ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _write_fixture(tmp_path: Path, png: bytes | None = None) -> None:
    logo = _ONE_PIXEL_PNG if png is None else png
    (tmp_path / "vendor").mkdir()
    (tmp_path / "logomarcas").mkdir()
    (tmp_path / "manifesto.json").write_text(_manifesto(), encoding="utf-8")
    (tmp_path / "municipios.json").write_text(_municipios(), encoding="utf-8")
    (tmp_path / "ufs.json").write_text(_ufs(), encoding="utf-8")
    (tmp_path / "paises.json").write_text(_paises(), encoding="utf-8")
    (tmp_path / "vendor" / "ol.js").write_text("var ol=1;", encoding="utf-8")
    (tmp_path / "vendor" / "ol.css").write_text(".ol {}", encoding="utf-8")
    (tmp_path / "vendor" / "topojson-client.min.js").write_text("var topojson=1;", encoding="utf-8")
    (tmp_path / "municipio_tse_ibge.csv").write_bytes(_bridge_csv())
    (tmp_path / "marcas.json").write_text(
        '{"22": {"cor": "#112233", "arquivo": "22.png"}}',
        encoding="utf-8",
    )
    (tmp_path / "logomarcas" / "22.png").write_bytes(logo)


def _manifesto() -> str:
    return json.dumps(
        {
            "municipios_objeto": "malha",
            "ufs_objeto": "ufs",
            "paises_objeto": "countries",
            "brasil_id": "076",
        },
    )


def _municipios() -> str:
    geometry: dict[str, object] = {
        "type": "Polygon",
        "properties": {"codarea": "1200138", "centroide": [-67.8, -9.8]},
    }
    return _topology("malha", (geometry,))


def _ufs() -> str:
    geometry: dict[str, object] = {
        "type": "Polygon",
        "properties": {"codarea": "12"},
    }
    return _topology("ufs", (geometry,))


def _paises() -> str:
    brazil: dict[str, object] = {"type": "Polygon", "id": "076"}
    other: dict[str, object] = {"type": "Polygon", "id": "242"}
    without_id: dict[str, object] = {"type": "Polygon", "properties": {"name": "Kosovo"}}
    return _topology("countries", (brazil, other, without_id))


def _topology(object_name: str, geometries: tuple[dict[str, object], ...]) -> str:
    document: dict[str, object] = {
        "type": "Topology",
        "objects": {
            object_name: {"type": "GeometryCollection", "geometries": list(geometries)},
        },
    }
    return json.dumps(document)


def _bridge_csv() -> bytes:
    header = (
        "DT_GERACAO;HH_GERACAO;CD_UF_TSE;CD_UF_IBGE;SG_UF;NM_UF;"
        "CD_MUNICIPIO_TSE;NM_MUNICIPIO_TSE;CD_MUNICIPIO_IBGE;NM_MUNICIPIO_IBGE"
    )
    bujari = '"04/10/2026";"09:00:06";"1";"12";"AC";"Bujari";"01007";"Bujari";"1200138";"Bujari"'
    sao_paulo = (
        '"04/10/2026";"09:00:06";"1";"35";"SP";"São Paulo";'
        '"71072";"São Paulo";"3550308";"São Paulo"'
    )
    return f"{header}\n{bujari}\n{sao_paulo}\n".encode("latin-1")


def test_load_reads_codes_logos_and_country_ids(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    loaded = LocalMeshAssets(tmp_path).load()
    assert loaded.codigos_municipio == frozenset({"1200138"})
    assert loaded.codigos_uf == frozenset({"12"})
    assert loaded.ids_pais == frozenset({"076", "242"})
    assert loaded.ponte.municipio_por_tse["01007"] == "1200138"
    assert loaded.ponte.municipio_por_tse["71072"] == "3550308"
    assert b"\xe3" in (tmp_path / "municipio_tse_ibge.csv").read_bytes()
    assert loaded.marcas[22].cor == "#112233"
    assert loaded.marcas[22].logo.startswith("data:image/png;base64,iVBORw0KGgo")
    assert loaded.ol_js == "var ol=1;"
    assert loaded.manifesto.brasil_id == "076"


def test_missing_mesh_names_the_file(tmp_path: Path) -> None:
    with pytest.raises(MeshMissingError) as error:
        LocalMeshAssets(tmp_path).load()
    assert error.value.nome == "downloads/malha/manifesto.json"


def test_svg_logo_uses_an_svg_data_uri(tmp_path: Path) -> None:
    _write_fixture(tmp_path, png=b"<svg xmlns='http://www.w3.org/2000/svg'/>")
    loaded = LocalMeshAssets(tmp_path).load()
    assert loaded.marcas[22].logo.startswith("data:image/svg+xml;base64,")


def test_text_logo_is_rejected(tmp_path: Path) -> None:
    _write_fixture(tmp_path, png=b"not-an-image")
    with pytest.raises(MarkInvalidError):
        LocalMeshAssets(tmp_path).load()


def test_missing_logo_names_the_file(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    (tmp_path / "logomarcas" / "22.png").unlink()
    with pytest.raises(MeshMissingError) as error:
        LocalMeshAssets(tmp_path).load()
    assert error.value.nome == "downloads/malha/logomarcas/22.png"
