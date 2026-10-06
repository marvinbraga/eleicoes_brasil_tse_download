"""Parses divulgação JSON into urna value objects. Malformed payloads stay domain errors."""

import json
from typing import cast

from eleicoes.domain.errors import (
    InvalidTurnoError,
    InvalidUrnaCodeError,
    UnexpectedTsePayloadError,
)
from eleicoes.domain.urna_models import (
    BallotSection,
    DivulgacaoConfig,
    MunicipioCode,
    PleitoCode,
    PublishedPleito,
    SecaoCode,
    SelectedHash,
    UrnaAddress,
    UrnaHash,
    UrnaTemplates,
    ZonaCode,
    select_download,
)
from eleicoes.domain.values import Turno, Uf


class UrnaJsonReader:
    def read_config(self, payload: bytes) -> DivulgacaoConfig:
        try:
            return _config(_object(payload))
        except InvalidUrnaCodeError as exc:
            raise UnexpectedTsePayloadError() from exc

    def read_sections(self, payload: bytes, uf: Uf) -> tuple[BallotSection, ...]:
        try:
            return _sections(_object(payload), uf)
        except InvalidUrnaCodeError as exc:
            raise UnexpectedTsePayloadError() from exc

    def read_auxiliary(self, payload: bytes) -> SelectedHash | None:
        try:
            return select_download(_hashes(_object(payload)))
        except InvalidUrnaCodeError as exc:
            raise UnexpectedTsePayloadError() from exc


def _config(root: dict[str, object]) -> DivulgacaoConfig:
    return DivulgacaoConfig(
        templates=_templates(root.get("arq")),
        pleitos=_pleitos(root.get("pl")),
    )


def _templates(value: object) -> UrnaTemplates:
    section = ""
    auxiliary = ""
    for item in _items(value):
        mapped = _require_mapping(item)
        kind = mapped.get("tp")
        directory = mapped.get("dir")
        if not isinstance(kind, str) or not isinstance(directory, str) or not directory:
            raise UnexpectedTsePayloadError()
        if kind == "cs" and not section:
            section = directory
        elif kind == "aux" and not auxiliary:
            auxiliary = directory
    return UrnaTemplates(section_config=section, auxiliary=auxiliary)


def _pleitos(value: object) -> tuple[PublishedPleito, ...]:
    found: list[PublishedPleito] = []
    for item in _items(value):
        pleito = _pleito(_require_mapping(item))
        if pleito is not None:
            found.append(pleito)
    return tuple(found)


def _pleito(mapped: dict[str, object]) -> PublishedPleito | None:
    cycle = mapped.get("c")
    if not isinstance(cycle, str) or not cycle:
        raise UnexpectedTsePayloadError()
    turnos = _turnos(mapped.get("e"))
    if not turnos:
        return None
    return PublishedPleito(code=PleitoCode(_digits(mapped.get("cd"))), cycle=cycle, turnos=turnos)


def _turnos(value: object) -> tuple[Turno, ...]:
    found: list[Turno] = []
    seen: set[int] = set()
    for item in _items(value):
        turno = _turno(_require_mapping(item).get("t"))
        if turno.value in seen:
            continue
        seen.add(turno.value)
        found.append(turno)
    return tuple(found)


def _turno(value: object) -> Turno:
    if isinstance(value, str) and value.strip().isdigit():
        number = int(value.strip())
    elif isinstance(value, int) and not isinstance(value, bool):
        number = value
    else:
        raise UnexpectedTsePayloadError()
    try:
        return Turno(number)
    except InvalidTurnoError as exc:
        raise UnexpectedTsePayloadError() from exc


def _sections(root: dict[str, object], uf: Uf) -> tuple[BallotSection, ...]:
    parsed: list[_Draft] = []
    for state in _items(root.get("abr")):
        parsed.extend(_state_sections(_require_mapping(state), uf))
    return _drop_aggregated(parsed)


def _state_sections(mapped: dict[str, object], uf: Uf) -> list["_Draft"]:
    code = mapped.get("cd")
    if not isinstance(code, str):
        raise UnexpectedTsePayloadError()
    if code.strip().casefold() != uf.code.casefold():
        return []
    drafts: list[_Draft] = []
    for city in _items(mapped.get("mu")):
        drafts.extend(_city_sections(_require_mapping(city), uf))
    return drafts


def _city_sections(mapped: dict[str, object], uf: Uf) -> list["_Draft"]:
    municipio = MunicipioCode(_digits(mapped.get("cd")))
    drafts: list[_Draft] = []
    for zone in _items(mapped.get("zon")):
        drafts.extend(_zone_sections(_require_mapping(zone), uf, municipio))
    return drafts


def _zone_sections(mapped: dict[str, object], uf: Uf, municipio: MunicipioCode) -> list["_Draft"]:
    zona = ZonaCode(_digits(mapped.get("cd")))
    drafts: list[_Draft] = []
    for section in _items(mapped.get("sec")):
        drafts.append(_draft(_require_mapping(section), uf, municipio, zona))
    return drafts


def _draft(
    mapped: dict[str, object],
    uf: Uf,
    municipio: MunicipioCode,
    zona: ZonaCode,
) -> "_Draft":
    secao = SecaoCode(_digits(mapped.get("ns")))
    aggregated = tuple(SecaoCode(_digits(code)) for code in _aggregated(mapped.get("nsa")))
    return _Draft(
        address=UrnaAddress(uf=uf, municipio=municipio, zona=zona, secao=secao),
        generated_on=_optional_text(mapped.get("da")),
        generated_at=_optional_text(mapped.get("ha")),
        aggregated=aggregated,
    )


class _Draft:
    def __init__(
        self,
        address: UrnaAddress,
        generated_on: str | None,
        generated_at: str | None,
        aggregated: tuple[SecaoCode, ...],
    ) -> None:
        self.address = address
        self.generated_on = generated_on
        self.generated_at = generated_at
        self.aggregated = aggregated


def _drop_aggregated(sections: list[_Draft]) -> tuple[BallotSection, ...]:
    # nsa lists sections already included in another box. They are not downloads.
    banned = _banned(sections)
    kept: list[BallotSection] = []
    for section in sections:
        address = section.address
        key = (address.municipio.value, address.zona.value, address.secao.value)
        if key in banned:
            continue
        kept.append(
            BallotSection(
                address=address,
                generated_on=section.generated_on,
                generated_at=section.generated_at,
            )
        )
    return tuple(kept)


def _banned(sections: list[_Draft]) -> set[tuple[str, str, str]]:
    banned: set[tuple[str, str, str]] = set()
    for section in sections:
        address = section.address
        for extra in section.aggregated:
            if extra.value == address.secao.value:
                continue
            banned.add((address.municipio.value, address.zona.value, extra.value))
    return banned


def _aggregated(value: object) -> tuple[object, ...]:
    if value is None or (isinstance(value, int) and not isinstance(value, bool)):
        return ()
    if isinstance(value, str):
        text = value.strip()
        return (text,) if text else ()
    if isinstance(value, list):
        found: list[object] = []
        for item in _items(value):
            found.extend(_aggregated_item(item))
        return tuple(found)
    raise UnexpectedTsePayloadError()


def _aggregated_item(value: object) -> tuple[object, ...]:
    if isinstance(value, str) or (isinstance(value, int) and not isinstance(value, bool)):
        return (value,)
    mapped = _mapping(value)
    if mapped is None or "ns" not in mapped:
        raise UnexpectedTsePayloadError()
    return (mapped["ns"],)


def _hashes(root: dict[str, object]) -> tuple[UrnaHash, ...]:
    parsed: list[UrnaHash] = []
    for item in _items(root.get("hashes")):
        mapped = _require_mapping(item)
        digest = mapped.get("hash")
        status = mapped.get("st")
        if not isinstance(digest, str) or not isinstance(status, str):
            raise UnexpectedTsePayloadError()
        parsed.append(
            UrnaHash(digest=digest, status=status, filenames=_filenames(mapped.get("arq")))
        )
    return tuple(parsed)


def _filenames(value: object) -> tuple[str, ...]:
    names: list[str] = []
    for item in _items(value):
        name = _require_mapping(item).get("nm")
        if not isinstance(name, str):
            raise UnexpectedTsePayloadError()
        names.append(name)
    return tuple(names)


def _digits(value: object) -> str:
    if isinstance(value, (bool, float)):
        raise UnexpectedTsePayloadError()
    if isinstance(value, int):
        if value < 0:
            raise UnexpectedTsePayloadError()
        return str(value)
    if isinstance(value, str) and value.strip().isdigit():
        return value.strip()
    raise UnexpectedTsePayloadError()


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, bool) or not isinstance(value, int):
        raise UnexpectedTsePayloadError()
    return str(value)


def _object(payload: bytes) -> dict[str, object]:
    try:
        loaded = cast(object, json.loads(payload.decode("utf-8-sig")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UnexpectedTsePayloadError() from exc
    mapped = _mapping(loaded)
    if mapped is None:
        raise UnexpectedTsePayloadError()
    return mapped


def _items(value: object) -> tuple[object, ...]:
    if not isinstance(value, list):
        raise UnexpectedTsePayloadError()
    copied: list[object] = []
    for item in value:
        copied.append(cast(object, item))
    return tuple(copied)


def _require_mapping(value: object) -> dict[str, object]:
    mapped = _mapping(value)
    if mapped is None:
        raise UnexpectedTsePayloadError()
    return mapped


def _mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    copied: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise UnexpectedTsePayloadError()
        copied[key] = cast(object, item)
    return copied
