"""Download of the measured meshes. Fetch is injected; nothing here opens the network."""

import io
import json
import zipfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace

import pytest

import eleicoes.use_cases.baixar_malha as mesh_download
from eleicoes.ports.malha import Manifesto
from eleicoes.use_cases.baixar_malha import (
    MEDIDOS,
    Medido,
    MeshSizeError,
    baixar_malha,
    exigir_centroide_municipal,
    exigir_contem,
    exigir_prefixo,
    exigir_tamanho,
    id_do_brasil,
    nome_do_objeto,
)

_BANNED: tuple[str, ...] = (
    "countries-50m",
    "intrarregiao=municipio",
    "geoftp",
    "leaflet",
    "maplibre",
    "mapbox",
)
Fetch = Callable[[str], bytes]


def _expected_size(body: bytes, expected: int, nome: str) -> None:
    """Stand-in bodies override the expected size only through this helper."""
    exigir_tamanho(body, expected, nome)


def test_measured_urls_and_sizes_match_the_spec() -> None:
    assert [(item.nome, item.url, item.tamanho) for item in MEDIDOS] == [
        ("vendor/ol.js", "https://unpkg.com/ol@10.11.0/dist/ol.js", 1_070_771),
        ("vendor/ol.css", "https://unpkg.com/ol@10.11.0/ol.css", 6_343),
        (
            "vendor/topojson-client.min.js",
            "https://unpkg.com/topojson-client@3.1.0/dist/topojson-client.min.js",
            7_169,
        ),
        (
            "municipios.json",
            "https://servicodados.ibge.gov.br/api/v2/malhas/BR"
            "?resolucao=5&qualidade=1&formato=application/json",
            1_626_114,
        ),
        (
            "ufs.json",
            "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
            "?intrarregiao=UF&qualidade=minima&formato=application/json",
            31_464,
        ),
        (
            "paises.json",
            "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json",
            107_761,
        ),
        (
            "municipio_tse_ibge.zip",
            "https://cdn.tse.jus.br/estatistica/sead/odsele/municipio_tse_ibge/municipio_tse_ibge.zip",
            139_031,
        ),
    ]


def test_production_checks_match_the_spec() -> None:
    assert [item.prefixo for item in MEDIDOS] == [b"var ol=", None, None, None, None, None, None]
    assert [item.contem for item in MEDIDOS] == [
        None,
        None,
        b"topojson",
        None,
        None,
        None,
        None,
    ]
    assert [item.csv_tamanho for item in MEDIDOS] == [None, None, None, None, None, None, 520_088]
    for item in MEDIDOS:
        for banned in _BANNED:
            assert banned not in item.url


def test_stand_in_body_uses_the_helper_expected_size() -> None:
    body = b"{}"
    _expected_size(body, len(body), "ufs.json")
    assert MEDIDOS[4].tamanho == 31_464


def test_wrong_size_is_rejected() -> None:
    with pytest.raises(MeshSizeError):
        exigir_tamanho(b"curto", 6_343, "vendor/ol.css")


def test_ol_js_must_start_with_the_global() -> None:
    with pytest.raises(MeshSizeError):
        exigir_prefixo(b"export default 1", b"var ol=")


def test_topojson_must_contain_the_global() -> None:
    with pytest.raises(MeshSizeError):
        exigir_contem(b"var d3=1", b"topojson")


def test_single_object_name_is_recorded() -> None:
    topology = {
        "type": "Topology",
        "objects": {"malha": {"type": "GeometryCollection", "geometries": []}},
    }
    assert nome_do_objeto(topology) == "malha"


def test_two_object_names_stop() -> None:
    topology = {"objects": {"a": {}, "b": {}}}
    with pytest.raises(MeshSizeError):
        nome_do_objeto(topology)


def test_brazil_id_accepts_only_076() -> None:
    assert id_do_brasil([{"id": "242"}, {"id": "076"}]) == "076"
    with pytest.raises(MeshSizeError):
        id_do_brasil([{"id": "242"}])


def test_municipal_centroid_must_exist_on_some_geometry() -> None:
    exigir_centroide_municipal([{"properties": {"codarea": "1", "centroide": [-1, -2]}}])
    with pytest.raises(MeshSizeError):
        exigir_centroide_municipal([{"properties": {"codarea": "1"}}])


def test_centroid_accepts_only_a_numeric_pair() -> None:
    exigir_centroide_municipal([{"properties": {"centroide": [-67.8, -9.8]}}])
    exigir_centroide_municipal(
        [
            {"properties": {"codarea": "1"}},
            {"properties": {"codarea": "2", "centroide": [-1, -2.5]}},
        ]
    )
    with pytest.raises(MeshSizeError):
        exigir_centroide_municipal([{"properties": {"centroide": [True, 1.0]}}])
    with pytest.raises(MeshSizeError):
        exigir_centroide_municipal([{"properties": {"centroide": [-1]}}])


def test_download_writes_the_manifest(tmp_path: Path) -> None:
    sample = _sample()
    called: list[str] = []
    manifesto = baixar_malha(tmp_path, _recording_fetch(sample.bodies, called), sample.medidos)

    assert manifesto == Manifesto("malha", "ufs", "countries", "076")
    assert called == [item.url for item in sample.medidos]
    for url in called:
        for banned in _BANNED:
            assert banned not in url
    assert (tmp_path / "vendor/ol.js").read_bytes().startswith(b"var ol=")
    assert (tmp_path / "vendor/ol.css").read_bytes() == sample.bodies[sample.medidos[1].url]
    assert b"topojson" in (tmp_path / "vendor/topojson-client.min.js").read_bytes()
    assert (tmp_path / "municipio_tse_ibge.csv").read_bytes() == sample.csv
    assert not (tmp_path / "municipio_tse_ibge.zip").exists()
    assert (tmp_path / "manifesto.json").read_text(encoding="utf-8") == _manifest_text(
        "malha", "ufs"
    )
    assert MEDIDOS[0].tamanho == 1_070_771
    assert MEDIDOS[6].csv_tamanho == 520_088


def test_zip_extracts_the_single_csv(tmp_path: Path) -> None:
    sample = _sample()
    baixar_malha(tmp_path, _recording_fetch(sample.bodies, []), sample.medidos)
    assert (tmp_path / "municipio_tse_ibge.csv").read_bytes() == sample.csv


def test_two_csv_members_stop(tmp_path: Path) -> None:
    body = _zip_bytes({"um.csv": b"a", "dois.csv": b"bb"})
    item = Medido(
        "municipio_tse_ibge.zip",
        "https://files.test/ponte.zip",
        len(body),
        csv_tamanho=1,
    )
    with pytest.raises(MeshSizeError):
        baixar_malha(tmp_path, lambda _url: body, (item,))


def test_inner_csv_must_match_the_injected_size(tmp_path: Path) -> None:
    body = _zip_bytes({"municipio_tse_ibge.csv": b"abc"})
    item = Medido(
        "municipio_tse_ibge.zip",
        "https://files.test/ponte.zip",
        len(body),
        csv_tamanho=1,
    )
    with pytest.raises(MeshSizeError):
        baixar_malha(tmp_path, lambda _url: body, (item,))


def test_corrupt_zip_stops(tmp_path: Path) -> None:
    body = b"not a zip"
    item = Medido(
        "municipio_tse_ibge.zip",
        "https://files.test/ponte.zip",
        len(body),
        csv_tamanho=1,
    )
    with pytest.raises(MeshSizeError):
        baixar_malha(tmp_path, lambda _url: body, (item,))


def test_download_rejects_the_wrong_injected_size(tmp_path: Path) -> None:
    body = b"a{}"
    item = Medido("vendor/ol.css", "https://files.test/ol.css", len(body) + 1)
    with pytest.raises(MeshSizeError):
        baixar_malha(tmp_path, lambda _url: body, (item,))


def test_download_rejects_a_bad_ol_prefix(tmp_path: Path) -> None:
    body = b"export default 1"
    item = Medido("vendor/ol.js", "https://files.test/ol.js", len(body), prefixo=b"var ol=")
    with pytest.raises(MeshSizeError):
        baixar_malha(tmp_path, lambda _url: body, (item,))


def test_download_rejects_topojson_without_the_name(tmp_path: Path) -> None:
    body = b"var d3=1"
    item = Medido(
        "vendor/topojson-client.min.js",
        "https://files.test/topo.js",
        len(body),
        contem=b"topojson",
    )
    with pytest.raises(MeshSizeError):
        baixar_malha(tmp_path, lambda _url: body, (item,))


def test_countries_use_the_countries_object(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[Mapping[str, object]] = []
    original = mesh_download.nome_do_objeto

    def spy(topology: Mapping[str, object]) -> str:
        seen.append(topology)
        return original(topology)

    monkeypatch.setattr(mesh_download, "nome_do_objeto", spy)
    sample = _sample()
    manifesto = baixar_malha(tmp_path, _recording_fetch(sample.bodies, []), sample.medidos)

    assert manifesto.paises_objeto == "countries"
    assert seen
    assert all("land" not in _object_names(topology) for topology in seen)
    with pytest.raises(MeshSizeError):
        id_do_brasil([{"id": "76"}])


def test_missing_countries_key_stops(tmp_path: Path) -> None:
    sample = _sample()
    replacement = _topology_bytes({"land": [{"id": "076"}]})
    bodies = dict(sample.bodies)
    medidos = _replace_body(sample.medidos, "paises.json", replacement, bodies)
    with pytest.raises(MeshSizeError):
        baixar_malha(tmp_path, _recording_fetch(bodies, []), medidos)


def test_script_prints_success_without_the_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    captured: dict[str, object] = {}

    def fake_download(
        destino: Path,
        fetch: Fetch,
        medidos: Sequence[Medido] = MEDIDOS,
    ) -> Manifesto:
        captured["destino"] = destino
        captured["fetch"] = fetch
        captured["medidos"] = medidos
        return Manifesto("foo", "BRUF", "countries", "076")

    def fake_get(url: str, timeout: int = 0) -> SimpleNamespace:
        assert url == "https://files.test/one"
        assert timeout == 120
        return SimpleNamespace(content=b"corpo")

    monkeypatch.setattr("scripts.baixar_malha.baixar_malha", fake_download)
    monkeypatch.setattr("scripts.baixar_malha.requests.get", fake_get)
    from scripts.baixar_malha import main

    assert main([]) == 0
    assert captured["destino"] == Path("downloads/malha")
    assert captured["medidos"] is MEDIDOS
    fetch = captured["fetch"]
    assert callable(fetch)
    assert fetch("https://files.test/one") == b"corpo"
    assert capsys.readouterr().out == (
        "Malha gravada em downloads/malha.\n"
        "As cores e as logomarcas ficam em downloads/malha/marcas.json "
        "e downloads/malha/logomarcas/.\n"
    )


def test_script_exits_1_when_the_mesh_disagrees(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    def fake_download(
        destino: Path,
        fetch: Fetch,
        medidos: Sequence[Medido] = MEDIDOS,
    ) -> Manifesto:
        del destino, fetch, medidos
        raise MeshSizeError("vendor/ol.js")

    monkeypatch.setattr("scripts.baixar_malha.baixar_malha", fake_download)
    from scripts.baixar_malha import main

    assert main([]) == 1
    captured = capsys.readouterr()
    assert captured.err == "A malha baixada não confere com a especificação.\n"
    assert captured.out == ""


class _Sample:
    def __init__(
        self,
        medidos: tuple[Medido, ...],
        bodies: dict[str, bytes],
        csv: bytes,
    ) -> None:
        self.medidos = medidos
        self.bodies = bodies
        self.csv = csv


def _sample() -> _Sample:
    ol_js = b"var ol=1"
    ol_css = b"a{}"
    topo = b"/* topojson */"
    municipalities = _topology_bytes(
        {
            "malha": [
                {"properties": {"codarea": "1"}},
                {"properties": {"codarea": "2", "centroide": [-1, -2]}},
            ]
        }
    )
    states = _topology_bytes({"ufs": [{"properties": {"codarea": "11"}}]})
    countries = _topology_bytes(
        {
            "countries": [{"id": "242"}, {"id": "076"}],
            "land": [],
        }
    )
    csv_body = b"CD;NM\n1;A\n"
    archive = _zip_bytes({"municipio_tse_ibge.csv": csv_body, "leia.txt": b"nota"})
    rows = (
        _row("vendor/ol.js", "https://files.test/ol.js", ol_js, prefixo=b"var ol="),
        _row("vendor/ol.css", "https://files.test/ol.css", ol_css),
        _row(
            "vendor/topojson-client.min.js",
            "https://files.test/topo.js",
            topo,
            contem=b"topojson",
        ),
        _row("municipios.json", "https://files.test/municipios.json", municipalities),
        _row("ufs.json", "https://files.test/ufs.json", states),
        _row("paises.json", "https://files.test/paises.json", countries),
        _row(
            "municipio_tse_ibge.zip",
            "https://files.test/ponte.zip",
            archive,
            csv_tamanho=len(csv_body),
        ),
    )
    bodies = {
        "https://files.test/ol.js": ol_js,
        "https://files.test/ol.css": ol_css,
        "https://files.test/topo.js": topo,
        "https://files.test/municipios.json": municipalities,
        "https://files.test/ufs.json": states,
        "https://files.test/paises.json": countries,
        "https://files.test/ponte.zip": archive,
    }
    return _Sample(rows, bodies, csv_body)


def _row(
    nome: str,
    url: str,
    body: bytes,
    *,
    prefixo: bytes | None = None,
    contem: bytes | None = None,
    csv_tamanho: int | None = None,
) -> Medido:
    return Medido(nome, url, len(body), prefixo, contem, csv_tamanho)


def _recording_fetch(bodies: Mapping[str, bytes], called: list[str]) -> Fetch:
    def fetch(url: str) -> bytes:
        called.append(url)
        return bodies[url]

    return fetch


def _topology_bytes(objects: Mapping[str, list[dict[str, object]]]) -> bytes:
    payload = {
        "type": "Topology",
        "objects": {
            name: {"type": "GeometryCollection", "geometries": geometries}
            for name, geometries in objects.items()
        },
    }
    return json.dumps(payload).encode("utf-8")


def _zip_bytes(members: Mapping[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    return buffer.getvalue()


def _replace_body(
    medidos: Sequence[Medido],
    nome: str,
    body: bytes,
    bodies: dict[str, bytes],
) -> tuple[Medido, ...]:
    updated: list[Medido] = []
    for item in medidos:
        if item.nome != nome:
            updated.append(item)
            continue
        bodies[item.url] = body
        updated.append(Medido(item.nome, item.url, len(body), item.prefixo, item.contem))
    return tuple(updated)


def _object_names(topology: Mapping[str, object]) -> set[str]:
    objects = topology.get("objects")
    if not isinstance(objects, dict):
        return set()
    return {key for key in objects if isinstance(key, str)}


def _manifest_text(municipios: str, ufs: str) -> str:
    payload = {
        "municipios_objeto": municipios,
        "ufs_objeto": ufs,
        "paises_objeto": "countries",
        "brasil_id": "076",
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
