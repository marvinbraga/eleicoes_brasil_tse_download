"""Sliding window that keeps TSE requests under the divulgação ceiling."""

import threading
from collections import deque
from typing import Final, Protocol

from eleicoes.domain.errors import InvalidRequestPaceError

HARD_REQUESTS_PER_SECOND: Final = 100
DEFAULT_REQUESTS_PER_SECOND: Final = 80
PARALLEL_SECTIONS: Final = 16
_WINDOW_MS: Final = 1000


class Clock(Protocol):
    def now_ms(self) -> int: ...


class Sleeper(Protocol):
    def sleep(self, seconds: float) -> None: ...


class RequestPace:
    """Callers wait here before each HTTP request. Not a decorator."""

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
        self._lock = threading.Lock()

    def before_request(self) -> None:
        while True:
            delay = self._claim_or_delay()
            if delay is None:
                return
            # Sleep outside the lock so another worker can take a free slot.
            self._sleeper.sleep(delay)

    def _claim_or_delay(self) -> float | None:
        with self._lock:
            return self._locked_claim()

    def _locked_claim(self) -> float | None:
        while True:
            now = self._clock.now_ms()
            self._expire(now)
            if len(self._stamps) < self._limit:
                self._stamps.append(now)
                return None
            wait_ms = _WINDOW_MS - (now - self._stamps[0])
            if wait_ms > 0:
                return wait_ms / _WINDOW_MS
            self._stamps.popleft()

    def _expire(self, now: int) -> None:
        while self._stamps and now - self._stamps[0] >= _WINDOW_MS:
            self._stamps.popleft()
