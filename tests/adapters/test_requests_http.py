import threading
from collections.abc import Iterator

import pytest
import requests
from requests.adapters import HTTPAdapter

from eleicoes.adapters.requests_http import RequestsHttpClient
from eleicoes.domain.errors import TransportError


class _Response:
    def __init__(
        self,
        payload: bytes | str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = 200
        self._payload = payload
        self.headers = {} if headers is None else headers
        self.closed = False
        self.chunk_size: int | None = None

    def iter_content(self, chunk_size: int = 1, decode_unicode: bool = False) -> Iterator[bytes]:
        del decode_unicode
        self.chunk_size = chunk_size
        if isinstance(self._payload, bytes):
            yield b""
            yield self._payload
        return

    @property
    def content(self) -> bytes | str:
        return self._payload

    def close(self) -> None:
        self.closed = True


class _Session:
    def __init__(self, response: _Response | None = None, explode: bool = False) -> None:
        self.response = response or _Response(b"abc")
        self.explode = explode
        self.stream: object = None

    def get(self, url: str, **kwargs: object) -> _Response:
        del url
        self.stream = kwargs.get("stream")
        if self.explode:
            raise requests.ConnectionError("offline")
        return self.response


def test_requests_client_streams_and_reads_without_opening_a_socket() -> None:
    session = _Session(_Response(b"abc"))
    client = RequestsHttpClient(session=session, timeout_seconds=5)  # type: ignore[arg-type]
    response = client.get("https://cdn.example/file.zip")
    assert response.status_code == 200
    assert tuple(response.body.iter_chunks(8)) == (b"abc",)
    assert session.response.chunk_size == 8
    assert session.stream is True
    assert response.body.read_bytes() == b"abc"
    response.body.close()
    assert session.response.closed is True


def test_requests_client_wraps_connection_errors() -> None:
    client = RequestsHttpClient(session=_Session(explode=True), timeout_seconds=1)  # type: ignore[arg-type]
    with pytest.raises(TransportError):
        client.get("https://cdn.example/file.zip")


def test_non_bytes_body_is_rejected() -> None:
    session = _Session(_Response("texto"))
    client = RequestsHttpClient(session=session)  # type: ignore[arg-type]
    response = client.get("https://cdn.example/meta")
    with pytest.raises(TransportError):
        response.body.read_bytes()


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("256", 256),
        ("0", 0),
        (None, None),
        ("", None),
        ("nope", None),
        ("-1", None),
        (" 12 ", 12),
        ("12.5", None),
    ],
)
def test_content_length_keeps_only_a_non_negative_integer(
    header: str | None,
    expected: int | None,
) -> None:
    headers = None if header is None else {"Content-Length": header}
    session = _Session(_Response(b"abc", headers))
    client = RequestsHttpClient(session=session)  # type: ignore[arg-type]
    response = client.get("https://cdn.example/file.dat")
    assert response.content_length == expected


def test_default_client_uses_one_session_per_thread_without_reading_a_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: list[requests.Session] = []

    class _RecordingSession(requests.Session):
        def __init__(self) -> None:
            super().__init__()
            self.calls: list[dict[str, object]] = []
            created.append(self)

        def get(self, url: str, **kwargs: object) -> _Response:  # type: ignore[override]
            del url
            self.calls.append(kwargs)
            return _Response(b"abc")

    monkeypatch.setattr("eleicoes.adapters.requests_http.requests.Session", _RecordingSession)
    client = RequestsHttpClient()
    assert created == []
    first = client.get("https://cdn.example/a")
    client.get("http://cdn.example/b")
    assert first.status_code == 200
    assert len(created) == 1
    assert created[0].calls[0]["stream"] is True
    assert created[0].calls[0]["timeout"] == 120.0
    for prefix in ("https://", "http://"):
        adapter = created[0].get_adapter(prefix)
        assert isinstance(adapter, HTTPAdapter)
        assert adapter._pool_connections == 1
        assert adapter._pool_maxsize == 1

    def other() -> None:
        client.get("https://cdn.example/c")

    thread = threading.Thread(target=other)
    thread.start()
    thread.join()
    assert len(created) == 2
    assert created[0] is not created[1]
