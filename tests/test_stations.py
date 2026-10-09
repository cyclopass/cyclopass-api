def test_health(client):
    reponse = client.get("/health")
    assert reponse.status_code == 200
    corps = reponse.get_json()
    assert corps["status"] == "ok"
    assert corps["version"] == open("VERSION").read().strip()


def test_liste_des_stations(client):
    stations = client.get("/stations").get_json()
    assert [s["nom"] for s in stations] == ["Gare Centrale", "Grand Place", "Vieux Port"]


def test_recherche_par_ville(client):
    stations = client.get("/recherche?ville=Lille").get_json()
    assert len(stations) == 2
    assert all(s["ville"] == "Lille" for s in stations)


def test_recherche_sans_ville_est_refusee(client):
    assert client.get("/recherche").status_code == 400


def test_route_inconnue_renvoie_du_json(client):
    reponse = client.get("/admin")
    assert reponse.status_code == 404
    assert "erreur" in reponse.get_json()


def test_entetes_de_securite(client):
    reponse = client.get("/stations")
    assert reponse.headers["X-Content-Type-Options"] == "nosniff"
