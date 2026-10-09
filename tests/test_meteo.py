"""L'API météo réelle n'est jamais appelée : on simule ses réponses."""
import pytest
import requests

from app import routes


class FausseReponse:
    def __init__(self, donnees, statut=200):
        self._donnees = donnees
        self.status_code = statut

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._donnees


@pytest.fixture
def appels(monkeypatch):
    historique = []

    def faux_get(url, **kwargs):
        historique.append(kwargs)
        return FausseReponse({"temperature": 14, "conditions": "nuageux", "interne": "x"})

    monkeypatch.setattr(routes.requests, "get", faux_get)
    return historique


def test_meteo_appel_securise(client, appels):
    reponse = client.get("/meteo?ville=Lille")
    assert reponse.status_code == 200
    assert reponse.get_json() == {"ville": "Lille", "temperature": 14, "conditions": "nuageux"}

    appel = appels[0]
    assert appel["timeout"] > 0                           # S6 : timeout obligatoire
    assert appel.get("verify", True) is True              # S4 : TLS vérifié
    assert "token" not in appel["params"]                 # S5 : token hors de l'URL
    assert appel["headers"]["Authorization"] == "Bearer token-de-test"


def test_meteo_indisponible(client, monkeypatch):
    def en_panne(url, **kwargs):
        raise requests.Timeout("trop long")

    monkeypatch.setattr(routes.requests, "get", en_panne)
    assert client.get("/meteo?ville=Lille").status_code == 502


def test_meteo_erreur_http_amont(client, monkeypatch):
    monkeypatch.setattr(routes.requests, "get", lambda url, **kw: FausseReponse({}, 500))
    assert client.get("/meteo?ville=Lille").status_code == 502


def test_meteo_ville_invalide(client, appels):
    assert client.get("/meteo", query_string={"ville": "<script>"}).status_code == 400
    assert appels == []


def test_meteo_sans_token(app, appels):
    app.config["METEO_API_TOKEN"] = None
    assert app.test_client().get("/meteo").status_code == 503
