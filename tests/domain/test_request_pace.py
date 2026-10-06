import pytest
from tests.urna_fakes import ManualClock, ManualSleeper

from eleicoes.domain.errors import InvalidRequestPaceError
from eleicoes.domain.request_pace import RequestPace


def test_eighty_requests_in_one_second_do_not_wait_and_the_next_one_does() -> None:
    clock = ManualClock()
    sleeper = ManualSleeper(clock)
    pace = RequestPace(clock, sleeper)
    for _ in range(80):
        pace.before_request()
    assert sleeper.waits == []
    pace.before_request()
    assert sleeper.waits == [1.0]


def test_limit_above_one_hundred_is_rejected() -> None:
    clock = ManualClock()
    with pytest.raises(InvalidRequestPaceError):
        RequestPace(clock, ManualSleeper(clock), limit=101)


def test_one_hundred_requests_are_allowed_and_zero_is_not() -> None:
    clock = ManualClock()
    pace = RequestPace(clock, ManualSleeper(clock), limit=100)
    for _ in range(100):
        pace.before_request()
    with pytest.raises(InvalidRequestPaceError):
        RequestPace(clock, ManualSleeper(clock), limit=0)


def test_a_request_outside_the_window_does_not_wait() -> None:
    clock = ManualClock()
    sleeper = ManualSleeper(clock)
    pace = RequestPace(clock, sleeper, limit=1)
    pace.before_request()
    clock.advance_ms(1000)
    pace.before_request()
    assert sleeper.waits == []


def test_bool_limit_is_rejected() -> None:
    clock = ManualClock()
    with pytest.raises(InvalidRequestPaceError):
        RequestPace(clock, ManualSleeper(clock), limit=True)
