from fastapi.testclient import TestClient

from eleicoes.composition.api import create_app
from eleicoes.ports.async_sql import AsyncPool


class _Pool:
    async def open(self, wait: bool = False, timeout: float = 30.0) -> None:
        if not wait and timeout < 0:
            raise AssertionError(timeout)

    async def close(self, timeout: float = 5.0) -> None:
        if timeout < 0:
            raise AssertionError(timeout)

    def connection(self) -> AsyncPool:
        raise AssertionError("health does not check out a connection")


def test_health_returns_ok() -> None:
    application = create_app(pool_factory=_Pool)
    response = TestClient(application).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
