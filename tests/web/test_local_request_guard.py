"""LocalRequestGuard refuses requests with a foreign Host and unsafe requests
whose Origin is another site."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from workbench.web.local_request_guard import LocalRequestGuard


def make_client() -> TestClient:
    app = FastAPI()

    @app.post("/api/act")
    def act() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/api/read")
    def read() -> dict[str, bool]:
        return {"ok": True}

    app.add_middleware(LocalRequestGuard)
    return TestClient(app, base_url="http://127.0.0.1")


def test_post_from_another_site_is_refused() -> None:
    response = make_client().post("/api/act", headers={"Origin": "http://evil.example"})
    assert response.status_code == 403


def test_post_with_null_origin_is_refused() -> None:
    assert make_client().post("/api/act", headers={"Origin": "null"}).status_code == 403


def test_post_from_the_local_page_passes() -> None:
    for origin in ("http://127.0.0.1:8760", "http://localhost:8760"):
        assert make_client().post("/api/act", headers={"Origin": origin}).status_code == 200


def test_post_without_origin_passes() -> None:
    assert make_client().post("/api/act").status_code == 200


def test_get_from_another_site_passes() -> None:
    response = make_client().get("/api/read", headers={"Origin": "http://evil.example"})
    assert response.status_code == 200


def test_get_with_a_local_host_passes() -> None:
    for host in ("127.0.0.1:8760", "localhost", "[::1]:8760"):
        assert make_client().get("/api/read", headers={"Host": host}).status_code == 200


def test_get_with_a_foreign_host_is_refused() -> None:
    response = make_client().get("/api/read", headers={"Host": "evil.example"})
    assert response.status_code == 403


def test_post_with_a_local_origin_and_a_foreign_host_is_refused() -> None:
    response = make_client().post(
        "/api/act", headers={"Origin": "http://127.0.0.1:8760", "Host": "evil.example"})
    assert response.status_code == 403
