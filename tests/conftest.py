from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _fresh_report_caches() -> Iterator[None]:
    from eleicoes.adapters.http.dependencies import clear_report_caches

    clear_report_caches()
    yield
    clear_report_caches()
