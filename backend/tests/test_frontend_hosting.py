from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_hosted_frontend_routes_serve_spa_and_assets(tmp_path, monkeypatch):
    assets = tmp_path / "assets"
    assets.mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><div id=\"root\"></div>", encoding="utf-8")
    (assets / "app.js").write_text("console.log('demo')", encoding="utf-8")
    settings = Settings(_env_file=None, frontend_dist_dir=tmp_path)
    monkeypatch.setattr("app.main.get_settings", lambda: settings)

    client = TestClient(create_app())

    assert client.get("/staff/setup").text == "<!doctype html><div id=\"root\"></div>"
    assert client.get("/assets/app.js").text == "console.log('demo')"
    assert client.get("/api/v1/health/live").json() == {"status": "ok"}
    assert client.get("/api/v1/unknown").status_code == 404
