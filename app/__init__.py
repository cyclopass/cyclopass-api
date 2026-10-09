"""CycloPass — API de vélos en libre-service."""
from pathlib import Path

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .config import charger_config
from .db import fermer_db, init_db
from .routes import bp

FICHIER_VERSION = Path(__file__).resolve().parent.parent / "VERSION"


def lire_version():
    try:
        return FICHIER_VERSION.read_text().strip()
    except OSError:
        return "inconnue"


def create_app(surcharges=None):
    app = Flask(__name__)
    app.config.update(charger_config(surcharges))
    app.json.ensure_ascii = False
    app.config["VERSION"] = lire_version()

    init_db(app.config["DATABASE_PATH"], seed=app.config["SEED_DEMO_DATA"])
    app.teardown_appcontext(fermer_db)
    app.register_blueprint(bp)

    @app.errorhandler(HTTPException)
    def erreur_http(err):
        return jsonify({"erreur": err.description}), err.code

    @app.errorhandler(Exception)
    def erreur_interne(err):
        # Jamais de stack trace côté client : elle part dans les logs.
        app.logger.exception("Erreur non gérée")
        return jsonify({"erreur": "Erreur interne"}), 500

    @app.after_request
    def entetes_securite(reponse):
        reponse.headers["X-Content-Type-Options"] = "nosniff"
        reponse.headers["Cache-Control"] = "no-store"
        return reponse

    return app
