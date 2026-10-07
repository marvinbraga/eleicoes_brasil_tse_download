import threading
from collections.abc import Iterator
from typing import Final

import requests
from requests.adapters import HTTPAdapter

from eleicoes.domain.errors import TransportError
from eleicoes.ports.http import BinaryBody, HttpResponse

DEFAULT_TIMEOUT_SECONDS: Final = 120.0
_POOL_SIZE: Final = 1


class RequestsHttpClient:
    """Adapta `requests` à porta HttpClient, sem carregar o corpo na construção."""

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._session = session
        self._timeout_seconds = timeout_seconds
        self._local = threading.local()

    def get(self, url: str) -> HttpResponse:
        try:
            response = self._active_session().get(
                url,
                stream=True,
                timeout=self._timeout_seconds,
            )
        except requests.RequestException as exc:
            raise TransportError("não foi possível contatar o TSE") from exc
        return _RequestsHttpResponse(response)

    def _active_session(self) -> requests.Session:
        if self._session is not None:
            return self._session
        current = getattr(self._local, "session", None)
        if isinstance(current, requests.Session):
            return current
        opened = _thread_session()
        self._local.session = opened
        return opened


def _thread_session() -> requests.Session:
    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=_POOL_SIZE, pool_maxsize=_POOL_SIZE)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


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

    @property
    def content_length(self) -> int | None:
        return _content_length(self._response.headers.get("Content-Length"))


def _content_length(value: str | None) -> int | None:
    if value is None:
        return None
    text = value.strip()
    if not text.isdecimal():
        return None
    return int(text)
