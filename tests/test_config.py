import pytest

from app import create_app
from app.config import ConfigurationError, charger_config


def test_mode_debug_toujours_desactive(app):
    assert app.debug is False


def test_staging_sans_secret_refuse_de_demarrer(monkeypatch):
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("API_KEYS", raising=False)
    with pytest.raises(ConfigurationError):
        charger_config()


def test_dev_genere_une_cle_ephemere(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    premiere, seconde = charger_config()["SECRET_KEY"], charger_config()["SECRET_KEY"]
    assert len(premiere) == 64 and premiere != seconde


def test_configuration_lue_depuis_l_environnement(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "s" * 32)
    monkeypatch.setenv("API_KEYS", "cle-a, cle-b")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "prod.db"))
    app = create_app()
    assert app.config["API_KEYS"] == ["cle-a", "cle-b"]
    assert app.config["DATABASE_PATH"].endswith("prod.db")
