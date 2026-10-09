"""Accès à la base SQLite."""
import os
import sqlite3

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS stations (
    id INTEGER PRIMARY KEY,
    nom TEXT NOT NULL,
    ville TEXT NOT NULL,
    velos INTEGER NOT NULL CHECK (velos >= 0)
);
CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY,
    usager TEXT NOT NULL,
    station_id INTEGER NOT NULL REFERENCES stations (id)
);
"""

STATIONS_DEMO = [
    ("Gare Centrale", "Lille", 12),
    ("Grand Place", "Lille", 4),
    ("Vieux Port", "Marseille", 9),
]


def connecter(chemin):
    dossier = os.path.dirname(chemin)
    if dossier:
        os.makedirs(dossier, exist_ok=True)
    conn = sqlite3.connect(chemin)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    if "db" not in g:
        g.db = connecter(current_app.config["DATABASE_PATH"])
    return g.db


def fermer_db(_exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(chemin, seed=True):
    conn = connecter(chemin)
    try:
        conn.executescript(SCHEMA)
        vide = conn.execute("SELECT COUNT(*) FROM stations").fetchone()[0] == 0
        if seed and vide:
            conn.executemany(
                "INSERT INTO stations (nom, ville, velos) VALUES (?, ?, ?)", STATIONS_DEMO
            )
        conn.commit()
    finally:
        conn.close()
