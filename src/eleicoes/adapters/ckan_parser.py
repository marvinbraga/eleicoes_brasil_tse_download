import json
from collections.abc import Mapping
from typing import cast
from urllib.parse import unquote, urlsplit

from eleicoes.domain.errors import CkanPayloadError, InvalidRemoteZipError
from eleicoes.domain.values import RemoteZip
from eleicoes.ports.ckan import CkanPackage, CkanPage

_SHA512_SUFFIX = ".zip.sha512"
_ZIP_SUFFIX = ".zip"


def parse_package_show(raw: str) -> CkanPackage | None:
    payload = _load_object(raw)
    success = payload.get("success")
    if success is False:
        return None
    if success is not True:
        raise CkanPayloadError("CKAN response has no success flag")
    result = _require_mapping(payload.get("result"), "result")
    return package_from_mapping(result)


def parse_package_search(raw: str) -> CkanPage:
    payload = _load_object(raw)
    if payload.get("success") is not True:
        raise CkanPayloadError("CKAN search failed")
    result = _require_mapping(payload.get("result"), "result")
    total = _count(result.get("count"))
    rows = result.get("results")
    if not isinstance(rows, list):
        raise CkanPayloadError("CKAN search has no results")
    packages = tuple(package_from_mapping(_require_mapping(row, "result")) for row in rows)
    return CkanPage(total=total, packages=packages)


def package_from_mapping(payload: Mapping[str, object]) -> CkanPackage:
    name = payload.get("name")
    if not isinstance(name, str) or not name:
        raise CkanPayloadError("CKAN package has no name")
    return CkanPackage(
        name=name,
        groups=_group_names(payload.get("groups")),
        archives=_archives(payload.get("resources")),
    )


def _load_object(raw: str) -> dict[str, object]:
    try:
        loaded = cast(object, json.loads(raw))
    except json.JSONDecodeError as exc:
        raise CkanPayloadError("CKAN response is not JSON") from exc
    return _require_mapping(loaded, "payload")


def _count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CkanPayloadError("CKAN search has no count")
    return value


def _require_mapping(value: object, label: str) -> dict[str, object]:
    mapped = _as_mapping(value)
    if mapped is None:
        raise CkanPayloadError(f"CKAN field {label} is not an object")
    return mapped


def _as_mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    mapped: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise CkanPayloadError("CKAN object has a non-string key")
        mapped[key] = item
    return mapped


def _group_names(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise CkanPayloadError("CKAN groups is not a list")
    names: list[str] = []
    for item in value:
        mapped = _as_mapping(item)
        if mapped is None:
            continue
        group_name = mapped.get("name")
        if isinstance(group_name, str) and group_name:
            names.append(group_name)
    return tuple(names)


def _archives(value: object) -> tuple[RemoteZip, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise CkanPayloadError("CKAN resources is not a list")
    archives: list[RemoteZip] = []
    seen: set[str] = set()
    for item in value:
        archive = _archive_from_resource(item)
        if archive is None or archive.url in seen:
            continue
        seen.add(archive.url)
        archives.append(archive)
    return tuple(archives)


def _archive_from_resource(value: object) -> RemoteZip | None:
    mapped = _as_mapping(value)
    if mapped is None:
        return None
    url = mapped.get("url")
    if not isinstance(url, str):
        return None
    filename = _zip_filename(url)
    if filename is None:
        return None
    try:
        return RemoteZip(url=url, filename=filename)
    except InvalidRemoteZipError:
        return None


def _zip_filename(url: str) -> str | None:
    path = unquote(urlsplit(url).path).rstrip("/")
    filename = path.split("/")[-1]
    lowered = filename.lower()
    if not filename or lowered.endswith(_SHA512_SUFFIX) or not lowered.endswith(_ZIP_SUFFIX):
        return None
    return filename
