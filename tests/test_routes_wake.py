from fastapi import FastAPI
from fastapi.testclient import TestClient

from workbench.routes_wake import WakeRoutes


class FakeBroadcaster:
    async def wake_all(self) -> tuple[str, ...]:
        return ("main", "CityBuilder")


def test_post_wake_returns_the_woken_names() -> None:
    app = FastAPI()
    app.include_router(WakeRoutes(FakeBroadcaster()).routes)
    response = TestClient(app).post("/api/wake")
    assert response.status_code == 200
    assert response.json() == {"woken": ["main", "CityBuilder"]}
