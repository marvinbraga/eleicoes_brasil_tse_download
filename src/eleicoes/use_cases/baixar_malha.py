"""Download the measured map meshes and record the object names."""

import io
import json
import zipfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from eleicoes.domain.errors import ElectionError
from eleicoes.ports.malha import Manifesto

Fetch = Callable[[str], bytes]

_MUNICIPALITIES: Final = "municipios.json"
_STATES: Final = "ufs.json"
_COUNTRIES_FILE: Final = "paises.json"
_CSV_NAME: Final = "municipio_tse_ibge.csv"
_MANIFEST: Final = "manifesto.json"
_COUNTRIES_OBJECT: Final = "countries"
_BRAZIL_ID: Final = "076"
_CENTROID_AXES: Final = 2
_OL_PREFIX: Final = b"var ol="
_TOPOJSON_SNIPPET: Final = b"topojson"


class MeshSizeError(ElectionError):
    def __init__(self, nome: str) -> None:
        self.nome = nome
        super().__init__(f"mesh does not match the specification: {nome}")


def _require_text(value: str, nome: str) -> None:
    if value.strip() == "":
        raise MeshSizeError(nome)


def _require_size(value: int, nome: str) -> None:
    if value < 1:
        raise MeshSizeError(nome)


def _require_blob(value: bytes | None, nome: str) -> None:
    if value is not None and value == b"":
        raise MeshSizeError(nome)


@dataclass(frozen=True, slots=True)
class Medido:
    nome: str
    url: str
    tamanho: int
    prefixo: bytes | None = None
    contem: bytes | None = None
    csv_tamanho: int | None = None

    def __post_init__(self) -> None:
        _require_text(self.nome, "nome")
        _require_text(self.url, self.nome)
        _require_size(self.tamanho, self.nome)
        _require_blob(self.prefixo, self.nome)
        _require_blob(self.contem, self.nome)
        if self.csv_tamanho is not None:
            _require_size(self.csv_tamanho, self.nome)


MEDIDOS: Final[tuple[Medido, ...]] = (
    Medido(
        "vendor/ol.js",
        "https://unpkg.com/ol@10.11.0/dist/ol.js",
        1_070_771,
        prefixo=_OL_PREFIX,
    ),
    Medido(
        "vendor/ol.css",
        "https://unpkg.com/ol@10.11.0/ol.css",
        6_343,
    ),
    Medido(
        "vendor/topojson-client.min.js",
        "https://unpkg.com/topojson-client@3.1.0/dist/topojson-client.min.js",
        7_169,
        contem=_TOPOJSON_SNIPPET,
    ),
    Medido(
        _MUNICIPALITIES,
        (
            "https://servicodados.ibge.gov.br/api/v2/malhas/BR"
            "?resolucao=5&qualidade=1&formato=application/json"
        ),
        1_626_114,
    ),
    Medido(
        _STATES,
        (
            "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
            "?intrarregiao=UF&qualidade=minima&formato=application/json"
        ),
        31_464,
    ),
    Medido(
        _COUNTRIES_FILE,
        "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json",
        107_761,
    ),
    Medido(
        "municipio_tse_ibge.zip",
        "https://cdn.tse.jus.br/estatistica/sead/odsele/municipio_tse_ibge/municipio_tse_ibge.zip",
        139_031,
        csv_tamanho=520_088,
    ),
)


@dataclass(frozen=True, slots=True)
class _Pieces:
    municipios_objeto: str | None = None
    ufs_objeto: str | None = None
    paises_objeto: str | None = None
    brasil_id: str | None = None


def exigir_tamanho(body: bytes, tamanho: int, nome: str) -> None:
    # requests.get(...).content is already decompressed. Never trust Content-Length.
    if len(body) != tamanho:
        raise MeshSizeError(nome)


def exigir_prefixo(body: bytes, prefixo: bytes) -> None:
    if not body.startswith(prefixo):
        raise MeshSizeError(prefixo.decode("utf-8", errors="replace"))


def exigir_contem(body: bytes, snippet: bytes) -> None:
    if snippet not in body:
        raise MeshSizeError(snippet.decode("utf-8", errors="replace"))


def nome_do_objeto(topology: Mapping[str, object]) -> str:
    return _only_name(_as_map(topology.get("objects"), "objects"))


def id_do_brasil(geometries: Sequence[Mapping[str, object]]) -> str:
    for geometry in geometries:
        if geometry.get("id") == _BRAZIL_ID:
            return _BRAZIL_ID
    raise MeshSizeError(_BRAZIL_ID)


def exigir_centroide_municipal(geometries: Sequence[Mapping[str, object]]) -> None:
    if any(_numeric_centroid(geometry) for geometry in geometries):
        return
    raise MeshSizeError("centroide")


def baixar_malha(
    destino: Path,
    fetch: Fetch,
    medidos: Sequence[Medido] = MEDIDOS,
) -> Manifesto:
    destino.mkdir(parents=True, exist_ok=True)
    pieces = _Pieces()
    for item in medidos:
        pieces = _merge(pieces, _store_one(destino, fetch, item))
    manifesto = _manifesto(pieces)
    _write_manifest(destino, manifesto)
    return manifesto


def _store_one(destino: Path, fetch: Fetch, item: Medido) -> _Pieces:
    body = fetch(item.url)
    _check_item(body, item)
    relative, payload, pieces = _prepare(item, body)
    _write(destino, relative, payload)
    return pieces


def _check_item(body: bytes, item: Medido) -> None:
    exigir_tamanho(body, item.tamanho, item.nome)
    if item.prefixo is not None:
        exigir_prefixo(body, item.prefixo)
    if item.contem is not None:
        exigir_contem(body, item.contem)


def _prepare(item: Medido, body: bytes) -> tuple[str, bytes, _Pieces]:
    if item.csv_tamanho is not None:
        return _CSV_NAME, _csv_from_zip(body, item.csv_tamanho), _Pieces()
    return item.nome, body, _pieces(item, body)


def _pieces(item: Medido, body: bytes) -> _Pieces:
    if item.nome == _MUNICIPALITIES:
        return _municipality_pieces(body)
    if item.nome == _STATES:
        return _state_pieces(body)
    if item.nome == _COUNTRIES_FILE:
        return _country_pieces(body)
    return _Pieces()


def _municipality_pieces(body: bytes) -> _Pieces:
    topology = _topology(body, _MUNICIPALITIES)
    name = nome_do_objeto(topology)
    exigir_centroide_municipal(_geometries(topology, name))
    return _Pieces(municipios_objeto=name)


def _state_pieces(body: bytes) -> _Pieces:
    topology = _topology(body, _STATES)
    return _Pieces(ufs_objeto=nome_do_objeto(topology))


def _country_pieces(body: bytes) -> _Pieces:
    # Countries keep the `countries` object and ignore `land`. Do not call nome_do_objeto.
    topology = _topology(body, _COUNTRIES_FILE)
    objects = _as_map(topology.get("objects"), _COUNTRIES_FILE)
    if _COUNTRIES_OBJECT not in objects:
        raise MeshSizeError(_COUNTRIES_FILE)
    brasil = id_do_brasil(_geometries(topology, _COUNTRIES_OBJECT))
    return _Pieces(paises_objeto=_COUNTRIES_OBJECT, brasil_id=brasil)


def _manifesto(pieces: _Pieces) -> Manifesto:
    municipios = pieces.municipios_objeto
    states = pieces.ufs_objeto
    countries = pieces.paises_objeto
    brasil = pieces.brasil_id
    if municipios is None or states is None or countries is None or brasil is None:
        raise MeshSizeError(_MANIFEST)
    return Manifesto(municipios, states, countries, brasil)


def _merge(current: _Pieces, extra: _Pieces) -> _Pieces:
    return _Pieces(
        municipios_objeto=_prefer(extra.municipios_objeto, current.municipios_objeto),
        ufs_objeto=_prefer(extra.ufs_objeto, current.ufs_objeto),
        paises_objeto=_prefer(extra.paises_objeto, current.paises_objeto),
        brasil_id=_prefer(extra.brasil_id, current.brasil_id),
    )


def _prefer(incoming: str | None, current: str | None) -> str | None:
    if incoming is not None:
        return incoming
    return current


def _write_manifest(destino: Path, manifesto: Manifesto) -> None:
    payload = {
        "municipios_objeto": manifesto.municipios_objeto,
        "ufs_objeto": manifesto.ufs_objeto,
        "paises_objeto": manifesto.paises_objeto,
        "brasil_id": manifesto.brasil_id,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    _write(destino, _MANIFEST, text.encode("utf-8"))


def _write(destino: Path, relative: str, body: bytes) -> None:
    path = destino / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


def _csv_from_zip(body: bytes, csv_tamanho: int) -> bytes:
    try:
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            names = [name for name in archive.namelist() if name.endswith(".csv")]
            if len(names) != 1:
                raise MeshSizeError("municipio_tse_ibge.zip")
            payload = archive.read(names[0])
    except zipfile.BadZipFile as exc:
        raise MeshSizeError("municipio_tse_ibge.zip") from exc
    if len(payload) != csv_tamanho:
        raise MeshSizeError(_CSV_NAME)
    return payload


def _topology(body: bytes, nome: str) -> dict[str, object]:
    try:
        loaded = cast(object, json.loads(body.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MeshSizeError(nome) from exc
    return _as_map(loaded, nome)


def _geometries(topology: Mapping[str, object], objeto: str) -> tuple[Mapping[str, object], ...]:
    objects = _as_map(topology.get("objects"), objeto)
    if objeto not in objects:
        raise MeshSizeError(objeto)
    collection = _as_map(objects[objeto], objeto)
    raw = collection.get("geometries")
    if not isinstance(raw, list):
        raise MeshSizeError(objeto)
    found: list[Mapping[str, object]] = []
    for item in raw:
        found.append(_as_map(cast(object, item), objeto))
    return tuple(found)


def _only_name(objects: Mapping[str, object]) -> str:
    names = tuple(objects)
    if len(names) != 1 or names[0] == "":
        raise MeshSizeError("objects")
    return names[0]


def _numeric_centroid(geometry: Mapping[str, object]) -> bool:
    properties = _mapping_or_none(geometry.get("properties"))
    if properties is None:
        return False
    return _numeric_pair(properties.get("centroide"))


def _numeric_pair(value: object) -> bool:
    if not isinstance(value, list) or len(value) != _CENTROID_AXES:
        return False
    return all(_number(cast(object, item)) for item in value)


def _number(value: object) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, int | float)


def _as_map(value: object, nome: str) -> dict[str, object]:
    mapped = _mapping_or_none(value)
    if mapped is None:
        raise MeshSizeError(nome)
    return mapped


def _mapping_or_none(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    mapped: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            return None
        mapped[key] = cast(object, item)
    return mapped
