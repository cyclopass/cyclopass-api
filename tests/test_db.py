import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.db import connecter, init_db


def test_init_db_est_idempotente_meme_en_parallele(tmp_path):
    # Simule plusieurs workers gunicorn qui démarrent en même temps.
    chemin = str(tmp_path / "parallele.db")
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: init_db(chemin), range(8)))
    conn = connecter(chemin)
    assert conn.execute("SELECT COUNT(*) FROM stations").fetchone()[0] == 3
    conn.close()


def test_le_stock_negatif_est_interdit_par_la_base(tmp_path):
    chemin = str(tmp_path / "contrainte.db")
    init_db(chemin)
    conn = connecter(chemin)
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        conn.execute("UPDATE stations SET velos = -1 WHERE id = 1")
    conn.close()
