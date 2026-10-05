from typing import Final
from urllib.parse import quote

from eleicoes.adapters.ckan_parser import parse_package_search, parse_package_show
from eleicoes.domain.errors import CkanPayloadError, UnexpectedHttpStatusError
from eleicoes.ports.ckan import CkanPackage, CkanPage
from eleicoes.ports.http import HttpClient

DEFAULT_CKAN_API: Final = "https://dadosabertos.tse.jus.br/api/3/action/"
HTTP_OK: Final = 200
HTTP_NOT_FOUND: Final = 404


class RequestsCkanGateway:
    """Adapta a API CKAN action para a porta CkanGateway."""

    def __init__(self, http: HttpClient, api_base: str = DEFAULT_CKAN_API) -> None:
        self._http = http
        self._api_base = api_base if api_base.endswith("/") else f"{api_base}/"

    def package_show(self, package_id: str) -> CkanPackage | None:
        url = f"{self._api_base}package_show?id={quote(package_id, safe='')}"
        raw, status = self._read(url)
        if status == HTTP_NOT_FOUND:
            return None
        if status != HTTP_OK:
            raise UnexpectedHttpStatusError(status, package_id)
        return parse_package_show(raw)

    def package_search(self, query: str, *, start: int, rows: int) -> CkanPage:
        url = f"{self._api_base}package_search?fq={quote(query, safe='')}&start={start}&rows={rows}"
        raw, status = self._read(url)
        if status != HTTP_OK:
            raise UnexpectedHttpStatusError(status, "package_search")
        return parse_package_search(raw)

    def _read(self, url: str) -> tuple[str, int]:
        response = self._http.get(url)
        try:
            payload = response.body.read_bytes()
        finally:
            response.body.close()
        return _decode(payload), response.status_code


def _decode(payload: bytes) -> str:
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CkanPayloadError("CKAN response is not UTF-8") from exc
