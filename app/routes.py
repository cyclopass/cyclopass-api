"""Routes de l'API CycloPass."""
import hmac
import re
from functools import wraps

import requests
from flask import Blueprint, abort, current_app, jsonify, request

from .db import get_db

bp = Blueprint("api", __name__)

MOTIF_VILLE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ' -]{1,64}$")
LONGUEUR_MAX_USAGER = 100


def cle_api_requise(vue):
    """Refuse la requête si l'en-tête X-API-Key ne correspond à aucune clé connue."""

    @wraps(vue)
    def verifier(*args, **kwargs):
        fournie = request.headers.get("X-API-Key", "")
        cles = current_app.config["API_KEYS"]
        if not fournie or not any(hmac.compare_digest(fournie, cle) for cle in cles):
            abort(401, description="Clé d'API manquante ou invalide")
        return vue(*args, **kwargs)

    return verifier


@bp.get("/health")
def health():
    get_db().execute("SELECT 1")
    return jsonify({"status": "ok"})


@bp.get("/stations")
def stations():
    rows = get_db().execute("SELECT id, nom, ville, velos FROM stations ORDER BY id").fetchall()
    return jsonify([dict(r) for r in rows])


@bp.get("/recherche")
def recherche():
    ville = request.args.get("ville", "").strip()
    if not ville:
        abort(400, description="Paramètre 'ville' obligatoire")
    # Requête paramétrée : la valeur n'est jamais interprétée comme du SQL.
    rows = get_db().execute(
        "SELECT id, nom, ville, velos FROM stations WHERE ville = ? ORDER BY id", (ville,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@bp.post("/reservations")
@cle_api_requise
def reserver():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, description="Corps JSON attendu")

    usager = data.get("usager")
    station_id = data.get("station_id")
    if not isinstance(usager, str) or not usager.strip() or len(usager) > LONGUEUR_MAX_USAGER:
        abort(400, description="'usager' doit être une chaîne non vide (100 caractères max)")
    if not isinstance(station_id, int) or isinstance(station_id, bool):
        abort(400, description="'station_id' doit être un entier")

    db = get_db()
    if db.execute("SELECT 1 FROM stations WHERE id = ?", (station_id,)).fetchone() is None:
        abort(404, description="Station inconnue")

    # Décrément conditionnel et atomique : impossible de passer sous zéro,
    # même avec deux réservations simultanées sur le dernier vélo.
    with db:
        maj = db.execute(
            "UPDATE stations SET velos = velos - 1 WHERE id = ? AND velos > 0", (station_id,)
        )
        if maj.rowcount == 0:
            abort(409, description="Plus aucun vélo disponible dans cette station")
        cur = db.execute(
            "INSERT INTO reservations (usager, station_id) VALUES (?, ?)",
            (usager.strip(), station_id),
        )
    return jsonify({"message": "Vélo réservé", "reservation_id": cur.lastrowid}), 201


@bp.get("/meteo")
def meteo():
    ville = request.args.get("ville", "Lille").strip()
    if not MOTIF_VILLE.match(ville):
        abort(400, description="Nom de ville invalide")

    token = current_app.config["METEO_API_TOKEN"]
    if not token:
        abort(503, description="Service météo non configuré")

    delai = current_app.config["METEO_TIMEOUT"]
    try:
        reponse = requests.get(
            current_app.config["METEO_API_URL"],
            params={"ville": ville},
            headers={"Authorization": f"Bearer {token}"},
            timeout=delai,
        )
        reponse.raise_for_status()
        donnees = reponse.json()
    except (requests.RequestException, ValueError):
        current_app.logger.warning("API météo indisponible pour %s", ville)
        abort(502, description="Service météo indisponible")

    return jsonify(
        {
            "ville": ville,
            "temperature": donnees.get("temperature"),
            "conditions": donnees.get("conditions"),
        }
    )
