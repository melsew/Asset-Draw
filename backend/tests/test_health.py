from fastapi.testclient import TestClient

from app.core import db, redis_client
from app.main import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_live_does_not_need_dependencies():
    r = _client().get("/api/v1/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ready_ok_when_dependencies_up(monkeypatch):
    monkeypatch.setattr(db, "check_database", lambda: None)
    monkeypatch.setattr(redis_client, "check_redis", lambda: None)
    r = _client().get("/api/v1/health/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}


def test_ready_503_when_database_down_and_no_details_leaked(monkeypatch):
    def boom():
        raise RuntimeError("password=secret host=internal")

    monkeypatch.setattr(db, "check_database", boom)
    monkeypatch.setattr(redis_client, "check_redis", lambda: None)
    r = _client().get("/api/v1/health/ready")
    assert r.status_code == 503
    body = r.json()
    assert body["checks"] == {"database": "unavailable", "redis": "ok"}
    assert "secret" not in r.text


def test_request_id_is_generated_and_echoed():
    c = _client()
    assert c.get("/api/v1/health/live").headers["x-request-id"]
    r = c.get("/api/v1/health/live", headers={"X-Request-ID": "abc-123"})
    assert r.headers["x-request-id"] == "abc-123"
