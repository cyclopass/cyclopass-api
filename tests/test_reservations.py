def velos(client, station_id):
    stations = client.get("/stations").get_json()
    return next(s["velos"] for s in stations if s["id"] == station_id)


def test_reservation_decremente_le_stock(client, auth):
    reponse = client.post("/reservations", json={"usager": "alice", "station_id": 1}, headers=auth)
    assert reponse.status_code == 201
    assert velos(client, 1) == 11


def test_reservation_sans_cle_api_est_refusee(client):
    reponse = client.post("/reservations", json={"usager": "alice", "station_id": 1})
    assert reponse.status_code == 401
    assert velos(client, 1) == 12


def test_reservation_avec_mauvaise_cle_est_refusee(client):
    reponse = client.post(
        "/reservations",
        json={"usager": "alice", "station_id": 1},
        headers={"X-API-Key": "mauvaise-cle"},
    )
    assert reponse.status_code == 401


def test_stock_ne_devient_jamais_negatif(client, auth):
    # Grand Place (id 2) a 4 vélos. Avant : 15 réservations → stock à -11.
    codes = [
        client.post("/reservations", json={"usager": f"u{i}", "station_id": 2}, headers=auth).status_code
        for i in range(6)
    ]
    assert codes == [201, 201, 201, 201, 409, 409]
    assert velos(client, 2) == 0


def test_station_inexistante(client, auth):
    reponse = client.post("/reservations", json={"usager": "alice", "station_id": 999}, headers=auth)
    assert reponse.status_code == 404


def test_corps_invalide(client, auth):
    for corps in ({}, {"usager": "", "station_id": 1}, {"usager": "a", "station_id": "1"},
                  {"usager": "a" * 101, "station_id": 1}, {"usager": "a", "station_id": True}):
        assert client.post("/reservations", json=corps, headers=auth).status_code == 400


def test_corps_non_json(client, auth):
    reponse = client.post("/reservations", data="pas du json", headers=auth)
    assert reponse.status_code == 400
    assert "erreur" in reponse.get_json()
