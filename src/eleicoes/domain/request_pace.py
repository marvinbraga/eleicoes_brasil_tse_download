"""Sliding window that keeps TSE requests under the divulgação ceiling."""

from collections import deque
from typing import Final, Protocol

from eleicoes.domain.errors import InvalidRequestPaceError

HARD_REQUESTS_PER_SECOND: Final = 100
DEFAULT_REQUESTS_PER_SECOND: Final = 80
_WINDOW_MS: Final = 1000


class Clock(Protocol):
    def now_ms(self) -> int: ...


class Sleeper(Protocol):
    def sleep(self, seconds: float) -> None: ...


class RequestPace:
    """One in-flight caller waits here before each HTTP request. Not a decorator."""

    def __init__(
        self,
        clock: Clock,
        sleeper: Sleeper,
        limit: int = DEFAULT_REQUESTS_PER_SECOND,
    ) -> None:
        # The divulgação page blocks an IP above 100 requests in any 1000 ms.
        if isinstance(limit, bool) or limit < 1 or limit > HARD_REQUESTS_PER_SECOND:
            raise InvalidRequestPaceError(limit)
        self._clock = clock
        self._sleeper = sleeper
        self._limit = limit
        self._stamps: deque[int] = deque()

    def before_request(self) -> None:
        while True:
            now = self._clock.now_ms()
            self._expire(now)
            if len(self._stamps) < self._limit:
                self._stamps.append(now)
                return
            wait_ms = _WINDOW_MS - (now - self._stamps[0])
            if wait_ms <= 0:
                self._stamps.popleft()
                continue
            self._sleeper.sleep(wait_ms / _WINDOW_MS)

    def _expire(self, now: int) -> None:
        while self._stamps and now - self._stamps[0] >= _WINDOW_MS:
            self._stamps.popleft()
