from app.core.config import Settings


def test_defaults_are_non_production():
    settings = Settings(_env_file=None)
    assert settings.environment != "production"
    assert settings.is_production is False


def test_production_flag(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert Settings(_env_file=None).is_production is True


def test_explicit_demo_mode_can_be_enabled_in_production():
    settings = Settings(_env_file=None, environment="production", demo_mode=True)
    assert settings.is_production is True
    assert settings.demo_mode is True


def test_postgres_url_uses_installed_psycopg_driver():
    url = "postgres://" + "db:5432/app"
    settings = Settings(_env_file=None, database_url=url)
    assert settings.database_url == "postgresql+psycopg://" + "db:5432/app"
