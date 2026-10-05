from collections.abc import Iterator
from typing import Final

import requests

from eleicoes.domain.errors import TransportError
from eleicoes.ports.http import BinaryBody, HttpResponse

DEFAULT_TIMEOUT_SECONDS: Final = 120.0


class RequestsHttpClient:
    """Adapta `requests` à porta HttpClient, sem carregar o corpo na construção."""

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._session = session if session is not None else requests.Session()
        self._timeout_seconds = timeout_seconds

    def get(self, url: str) -> HttpResponse:
        try:
            response = self._session.get(url, stream=True, timeout=self._timeout_seconds)
        except requests.RequestException as exc:
            raise TransportError("não foi possível contatar o TSE") from exc
        return _RequestsHttpResponse(response)


class _RequestsBody:
    def __init__(self, response: requests.Response) -> None:
        self._response = response

    def iter_chunks(self, chunk_size: int) -> Iterator[bytes]:
        for chunk in self._response.iter_content(chunk_size=chunk_size):
            if chunk:
                yield chunk

    def read_bytes(self) -> bytes:
        content = self._response.content
        if not isinstance(content, bytes):
            raise TransportError("corpo HTTP inválido")
        return content

    def close(self) -> None:
        self._response.close()


class _RequestsHttpResponse:
    def __init__(self, response: requests.Response) -> None:
        self._response = response
        self._body = _RequestsBody(response)

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def body(self) -> BinaryBody:
        return self._body
