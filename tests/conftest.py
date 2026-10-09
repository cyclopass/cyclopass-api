import pytest

from app import create_app

CLE_TEST = "cle-de-test"


@pytest.fixture
def app(tmp_path):
    return create_app(
        {
            "APP_ENV": "test",
            "DATABASE_PATH": str(tmp_path / "test.db"),
            "API_KEYS": [CLE_TEST],
            "METEO_API_TOKEN": "token-de-test",
            "SEED_DEMO_DATA": True,
        }
    )


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth():
    return {"X-API-Key": CLE_TEST}
