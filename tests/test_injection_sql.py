"""Non-régression de la faille S1 : la « recherche bizarre » signalée par le client."""
import pytest

CHARGES_MALVEILLANTES = [
    "x' OR '1'='1",
    "Lille' OR 1=1 --",
    "' UNION SELECT id, usager, usager, station_id FROM reservations --",
    "'; DROP TABLE stations; --",
]


@pytest.mark.parametrize("charge", CHARGES_MALVEILLANTES)
def test_injection_sql_ne_renvoie_rien(client, charge):
    reponse = client.get("/recherche", query_string={"ville": charge})
    assert reponse.status_code == 200
    assert reponse.get_json() == []


def test_injection_ne_detruit_pas_la_base(client):
    client.get("/recherche", query_string={"ville": "'; DROP TABLE stations; --"})
    assert len(client.get("/stations").get_json()) == 3


def test_apostrophe_legitime_ne_fait_plus_planter(client):
    # Avant : erreur 500 (syntax error) dès qu'une ville contenait une apostrophe.
    reponse = client.get("/recherche", query_string={"ville": "Villeneuve-d'Ascq"})
    assert reponse.status_code == 200
    assert reponse.get_json() == []
