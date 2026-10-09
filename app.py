# CycloPass - API vélos en libre-service
# Code historique (2019), maintenu par une seule personne qui a quitté l'entreprise.
import sqlite3

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
app.config["SECRET_KEY"] = "cyclopass-2019-super-secret"

DB = "cyclopass.db"
METEO_API_TOKEN = "mt_live_9f8Kq2LxP4vR7zT1wY6bN3cJ5hD0sA"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS stations (id INTEGER PRIMARY KEY, nom TEXT, ville TEXT, velos INTEGER)")
    conn.execute("CREATE TABLE IF NOT EXISTS reservations (id INTEGER PRIMARY KEY, usager TEXT, station_id INTEGER)")
    if conn.execute("SELECT COUNT(*) FROM stations").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO stations (nom, ville, velos) VALUES (?, ?, ?)",
            [("Gare Centrale", "Lille", 12), ("Grand Place", "Lille", 4), ("Vieux Port", "Marseille", 9)],
        )
    conn.commit()
    conn.close()


@app.route("/stations")
def stations():
    conn = get_db()
    rows = conn.execute("SELECT * FROM stations").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/recherche")
def recherche():
    ville = request.args.get("ville", "")
    conn = get_db()
    rows = conn.execute("SELECT * FROM stations WHERE ville = '%s'" % ville).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/reservations", methods=["POST"])
def reserver():
    data = request.get_json()
    conn = get_db()
    conn.execute("INSERT INTO reservations (usager, station_id) VALUES (?, ?)", (data["usager"], data["station_id"]))
    conn.execute("UPDATE stations SET velos = velos - 1 WHERE id = ?", (data["station_id"],))
    conn.commit()
    conn.close()
    return jsonify({"message": "Vélo réservé"}), 201


@app.route("/meteo")
def meteo():
    ville = request.args.get("ville", "Lille")
    r = requests.get(
        "https://api.meteo.example.com/v1/now",
        params={"ville": ville, "token": METEO_API_TOKEN},
        verify=False,
    )
    return jsonify(r.json())


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
