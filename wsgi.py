"""Point d'entrée pour le serveur de production (gunicorn wsgi:app)."""
from app import create_app

app = create_app()
