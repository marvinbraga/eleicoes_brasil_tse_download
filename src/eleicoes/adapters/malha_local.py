"""Reads the local TopoJSON mesh, the TSE-IBGE bridge, and party marks."""

import base64
import csv
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Final, cast

from eleicoes.domain.mapa import (
    InvalidPonteError,
    Marca,
    MarkInvalidError,
    MeshMismatchError,
    MeshMissingError,
    PonteTseIbge,
    ponte_de_linhas,
)
from eleicoes.ports.malha import MalhaCarregada, Manifesto

_MESH_ROOT: Final = "downloads/malha"
_TEXT_FILES: Final[tuple[str, ...]] = (
    "manifesto.json",
    "municipios.json",
    "ufs.json",
    "paises.json",
    "vendor/ol.js",
    "vendor/ol.css",
    "vendor/topojson-client.min.js",
    "municipio_tse_ibge.csv",
    "marcas.json",
)
_CSV_NAME: Final = "municipio_tse_ibge.csv"
_MARKS_NAME: Final = "marcas.json"
_PNG_MAGIC: Final = b"\x89PNG"
_SVG_MAGIC: Final = b"<svg"
_XML_MAGIC: Final = b"<?xml"
_COLOR: Final = re.compile(r"^#[0-9A-Fa-f]{6}$")
_MAX_PARTY: Final = 99
_PNG_MEDIA: Final = "image/png"
_SVG_MEDIA: Final = "image/svg+xml"
_EXTERIOR_NAME: Final = "exterior.csv"
_EXTERIOR_COLUMNS: Final = ["codigo", "nome", "lon", "lat"]
_TSE_DIGITS: Final = 5
_MAX_LON: Final = 180.0
_MAX_LAT: Final = 90.0


class LocalMeshAssets:
    def __init__(self, raiz: Path, exterior: Path | None = None) -> None:
        self._raiz = raiz
        self._exterior = exterior

    def load(self) -> MalhaCarregada:
        texts = self._texts()
        manifesto = _manifesto(texts["manifesto.json"])
        municipalities = texts["municipios.json"]
        states = texts["ufs.json"]
        countries = texts["paises.json"]
        return MalhaCarregada(
            manifesto=manifesto,
            municipios=municipalities,
            ufs=states,
            paises=countries,
            ol_js=texts["vendor/ol.js"],
            ol_css=texts["vendor/ol.css"],
            topojson_js=texts["vendor/topojson-client.min.js"],
            ponte=_bridge(texts[_CSV_NAME]),
            marcas=self._marks(texts[_MARKS_NAME]),
            codigos_municipio=codigos_no_objeto(
                _json_object(municipalities, "municipios.json"),
                manifesto.municipios_objeto,
                "codarea",
            ),
            codigos_uf=codigos_no_objeto(
                _json_object(states, "ufs.json"),
                manifesto.ufs_objeto,
                "codarea",
            ),
            ids_pais=codigos_no_objeto(
                _json_object(countries, "paises.json"),
                manifesto.paises_objeto,
                "id",
            ),
            exterior=self._coordinates(),
        )

    def _coordinates(self) -> dict[str, tuple[float, float]]:
        if self._exterior is None:
            return {}
        if not self._exterior.is_file():
            raise MeshMissingError(_EXTERIOR_NAME)
        return _exterior(self._exterior.read_text(encoding="utf-8"))

    def _texts(self) -> dict[str, str]:
        return {name: self._read(name) for name in _TEXT_FILES}

    def _read(self, relative: str) -> str:
        path = self._raiz / relative
        if not path.is_file():
            raise MeshMissingError(f"{_MESH_ROOT}/{relative}")
        # The TSE bridge is latin-1. UTF-8 rejects the ã byte in municipal names.
        encoding = "latin-1" if relative == _CSV_NAME else "utf-8"
        return path.read_text(encoding=encoding)

    def _marks(self, raw: str) -> dict[int, Marca]:
        found: dict[int, Marca] = {}
        for key, value in _json_object(raw, _MARKS_NAME).items():
            party = _party(key)
            color, filename = _mark_fields(value, party)
            found[party] = Marca(color, self._logo(party, filename))
        return found

    def _logo(self, party: int, filename: str) -> str:
        relative = f"logomarcas/{filename}"
        path = self._raiz / relative
        if not path.is_file():
            raise MeshMissingError(f"{_MESH_ROOT}/{relative}")
        payload = path.read_bytes()
        encoded = base64.standard_b64encode(payload).decode("ascii")
        return f"data:{_media(payload, party)};base64,{encoded}"


def codigos_no_objeto(
    topology: Mapping[str, object],
    objeto: str,
    campo: str,
) -> frozenset[str]:
    codes: set[str] = set()
    for item in _geometries(topology, objeto):
        code = _geometry_code(item, objeto, campo)
        if code is not None:
            codes.add(code)
    return frozenset(codes)


def _geometries(topology: Mapping[str, object], objeto: str) -> tuple[object, ...]:
    objects = _as_map(topology.get("objects"), objeto)
    if objeto not in objects:
        raise MeshMismatchError(objeto)
    raw = _as_map(objects[objeto], objeto).get("geometries")
    if not isinstance(raw, list):
        raise MeshMismatchError(objeto)
    return tuple(cast(object, item) for item in raw)


def _geometry_code(item: object, objeto: str, campo: str) -> str | None:
    geometry = _as_map(item, objeto)
    if campo == "id":
        value = geometry.get("id")
        if value is None:
            return None
        return _as_text(value, objeto)
    if campo == "codarea":
        properties = _as_map(geometry.get("properties"), objeto)
        return _as_text(properties.get("codarea"), objeto)
    raise MeshMismatchError(campo)


def _manifesto(raw: str) -> Manifesto:
    data = _json_object(raw, "manifesto.json")
    return Manifesto(
        municipios_objeto=_as_text(data.get("municipios_objeto"), "manifesto.json"),
        ufs_objeto=_as_text(data.get("ufs_objeto"), "manifesto.json"),
        paises_objeto=_as_text(data.get("paises_objeto"), "manifesto.json"),
        brasil_id=_as_text(data.get("brasil_id"), "manifesto.json"),
    )


def _bridge(raw: str) -> PonteTseIbge:
    rows = [_csv_row(row) for row in csv.DictReader(raw.splitlines(), delimiter=";")]
    return ponte_de_linhas(rows)


def _csv_row(raw_row: object) -> dict[str, str]:
    if not isinstance(raw_row, dict):
        raise InvalidPonteError
    row: dict[str, str] = {}
    for key, value in raw_row.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise InvalidPonteError
        row[key] = value
    return row


def _exterior(raw: str) -> dict[str, tuple[float, float]]:
    reader = csv.DictReader(raw.splitlines())
    if reader.fieldnames != _EXTERIOR_COLUMNS:
        raise MeshMismatchError(_EXTERIOR_NAME)
    found: dict[str, tuple[float, float]] = {}
    for row in reader:
        code, coordinate = _exterior_row(row)
        if code in found:
            raise MeshMismatchError(_EXTERIOR_NAME)
        found[code] = coordinate
    return found


def _exterior_row(row: dict[str | None, object]) -> tuple[str, tuple[float, float]]:
    code = row.get("codigo")
    if None in row or not isinstance(code, str) or not _tse_code(code):
        raise MeshMismatchError(_EXTERIOR_NAME)
    return code, (_degrees(row.get("lon"), _MAX_LON), _degrees(row.get("lat"), _MAX_LAT))


def _tse_code(code: str) -> bool:
    return len(code) == _TSE_DIGITS and code.isascii() and code.isdigit()


def _degrees(value: object, limit: float) -> float:
    if not isinstance(value, str):
        raise MeshMismatchError(_EXTERIOR_NAME)
    try:
        degrees = float(value)
    except ValueError as exc:
        raise MeshMismatchError(_EXTERIOR_NAME) from exc
    if not -limit <= degrees <= limit:
        raise MeshMismatchError(_EXTERIOR_NAME)
    return degrees


def _party(key: str) -> int:
    if not key.isdigit():
        raise MeshMismatchError(_MARKS_NAME)
    party = int(key)
    if party > _MAX_PARTY:
        raise MarkInvalidError(party)
    return party


def _mark_fields(value: object, party: int) -> tuple[str, str]:
    if not isinstance(value, dict):
        raise MarkInvalidError(party)
    mapped = _as_map(value, _MARKS_NAME)
    color = _mark_text(mapped.get("cor"), party)
    filename = _mark_text(mapped.get("arquivo"), party)
    if _COLOR.fullmatch(color) is None or not _safe_basename(filename):
        raise MarkInvalidError(party)
    return color, filename


def _mark_text(value: object, party: int) -> str:
    if not isinstance(value, str):
        raise MarkInvalidError(party)
    return value


def _safe_basename(filename: str) -> bool:
    return filename != "" and "/" not in filename and "\\" not in filename and ".." not in filename


def _media(payload: bytes, party: int) -> str:
    if payload.startswith(_PNG_MAGIC):
        return _PNG_MEDIA
    if payload.startswith(_SVG_MAGIC) or payload.startswith(_XML_MAGIC):
        return _SVG_MEDIA
    raise MarkInvalidError(party)


def _json_object(raw: str, nome: str) -> dict[str, object]:
    try:
        loaded = cast(object, json.loads(raw))
    except json.JSONDecodeError as exc:
        raise MeshMismatchError(nome) from exc
    return _as_map(loaded, nome)


def _as_map(value: object, nome: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise MeshMismatchError(nome)
    copied: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise MeshMismatchError(nome)
        copied[key] = cast(object, item)
    return copied


def _as_text(value: object, nome: str) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise MeshMismatchError(nome)
    return str(value)
