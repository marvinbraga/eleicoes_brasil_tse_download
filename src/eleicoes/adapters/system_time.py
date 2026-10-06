"""Wall clock and sleeper used by the divulgação pace."""

import time


class MonotonicClock:
    def now_ms(self) -> int:
        return int(time.monotonic() * 1000)


class BlockingSleeper:
    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)
