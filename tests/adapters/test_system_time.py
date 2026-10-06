import time

import pytest

from eleicoes.adapters.system_time import BlockingSleeper, MonotonicClock


def test_monotonic_clock_reports_milliseconds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "monotonic", lambda: 2.5)
    assert MonotonicClock().now_ms() == 2500


def test_blocking_sleeper_delegates_to_time_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[float] = []
    monkeypatch.setattr("eleicoes.adapters.system_time.time.sleep", seen.append)
    BlockingSleeper().sleep(0.25)
    assert seen == [0.25]
