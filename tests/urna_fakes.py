"""In-memory clock, sleeper, and HTTP queue for urna tests. No sockets."""

from tests.support import FakeHttpResponse


class ManualClock:
    def __init__(self) -> None:
        self.milliseconds = 0

    def now_ms(self) -> int:
        return self.milliseconds

    def advance_ms(self, amount: int) -> None:
        self.milliseconds += amount


class ManualSleeper:
    def __init__(self, clock: ManualClock, http: "QueueHttp | None" = None) -> None:
        self.clock = clock
        self.http = http
        self.waits: list[float] = []
        self.urls_when_sleeping: list[int] = []

    def sleep(self, seconds: float) -> None:
        self.waits.append(seconds)
        if self.http is not None:
            self.urls_when_sleeping.append(len(self.http.urls))
        self.clock.advance_ms(int(seconds * 1000))


class QueueHttp:
    """Returns each scripted response once. An unknown URL fails the test."""

    def __init__(self, routes: dict[str, list[tuple[int, bytes]]]) -> None:
        self._routes = {url: list(items) for url, items in routes.items()}
        self.urls: list[str] = []

    def get(self, url: str) -> FakeHttpResponse:
        self.urls.append(url)
        pending = self._routes.get(url)
        if not pending:
            raise AssertionError(url)
        status, payload = pending.pop(0)
        return FakeHttpResponse(status, payload)
