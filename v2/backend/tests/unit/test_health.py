from __future__ import annotations

from fastapi.testclient import TestClient

from domcek_bot.api.app import create_app
from domcek_bot.config import Settings
from domcek_bot.infrastructure.database import DatabaseUnavailableError


class FakeDatabase:
    def __init__(self, *, healthy: bool) -> None:
        self.healthy = healthy
        self.closed = False

    async def ping(self) -> None:
        if not self.healthy:
            raise DatabaseUnavailableError("unavailable")

    async def close(self) -> None:
        self.closed = True


def test_liveness_does_not_depend_on_database(settings: Settings) -> None:
    database = FakeDatabase(healthy=False)
    with TestClient(create_app(settings=settings, database=database)) as client:
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive", "version": "0.1.0", "environment": "test"}
    assert response.headers["X-Correlation-ID"]
    assert database.closed


def test_readiness_is_ready_with_database(settings: Settings) -> None:
    with TestClient(create_app(settings=settings, database=FakeDatabase(healthy=True))) as client:
        response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dependencies": {"database": {"status": "healthy"}},
    }


def test_readiness_is_503_without_database(settings: Settings) -> None:
    with TestClient(create_app(settings=settings, database=FakeDatabase(healthy=False))) as client:
        response = client.get("/health/ready", headers={"X-Correlation-ID": "e1-test"})
    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "dependencies": {"database": {"status": "unhealthy"}},
    }
    assert response.headers["X-Correlation-ID"] == "e1-test"
