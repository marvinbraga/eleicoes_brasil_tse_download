from collections.abc import Iterator
from typing import Protocol


class BinaryBody(Protocol):
    def iter_chunks(self, chunk_size: int) -> Iterator[bytes]: ...

    def read_bytes(self) -> bytes: ...

    def close(self) -> None: ...


class HttpResponse(Protocol):
    @property
    def status_code(self) -> int: ...

    @property
    def body(self) -> BinaryBody: ...

    @property
    def content_length(self) -> int | None: ...


class HttpClient(Protocol):
    def get(self, url: str) -> HttpResponse: ...
