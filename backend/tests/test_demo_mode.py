from app.core import demo_store
from app.core.config import Settings


def test_explicit_demo_mode_stays_available_with_production_settings(monkeypatch):
    settings = Settings(_env_file=None, environment="production", demo_mode=True)
    monkeypatch.setattr(demo_store, "get_settings", lambda: settings)

    assert demo_store.is_demo_mode() is True


def test_explicitly_disabling_demo_mode_overrides_development_default(monkeypatch):
    settings = Settings(_env_file=None, environment="development", demo_mode=False)
    monkeypatch.setattr(demo_store, "get_settings", lambda: settings)

    assert demo_store.is_demo_mode() is False
