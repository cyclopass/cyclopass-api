# CycloPass API

API des vélos en libre-service CycloPass : liste des stations, recherche par ville, réservation d'un vélo et météo locale.

> Ce dépôt est la reprise du code legacy de 2019. L'audit de départ est dans [`docs/AUDIT.md`](docs/AUDIT.md).

## Prérequis

- **Python 3.12** (`python3 --version`)
- Git

## Lancer l'application en local

```bash
git clone https://github.com/cyclopass/cyclopass-api.git
cd cyclopass-api

python3 -m venv .venv
source .venv/bin/activate          # Windows (Git Bash) : source .venv/Scripts/activate
pip install -r requirements-dev.txt

export API_KEYS=cle-dev-locale     # clé à envoyer dans l'en-tête X-API-Key pour réserver
flask --app wsgi run --port 8000   # → http://localhost:8000
```

Vérifier que tout répond :

```bash
curl http://localhost:8000/health
curl http://localhost:8000/stations
curl "http://localhost:8000/recherche?ville=Lille"
curl -X POST http://localhost:8000/reservations \
     -H "X-API-Key: cle-dev-locale" -H "Content-Type: application/json" \
     -d '{"usager": "alice", "station_id": 1}'
```

> Sur Mac, le port 5000 est pris par le récepteur AirPlay : c'est pour ça qu'on utilise 8000.

La base SQLite (`cyclopass.db`) est créée et remplie de 3 stations de démonstration au premier démarrage.

## Lancer avec Docker

```bash
docker build -t cyclopass-api .
docker run --rm -p 8000:8000 -e SECRET_KEY=change-moi -e API_KEYS=cle-dev-locale cyclopass-api
```

L'image tourne avec **gunicorn**, sous un **utilisateur non-root** (uid 10001), sans mode debug. Elle inclut un healthcheck sur `/health`.

Les images officielles sont publiées par la CI sur `ghcr.io/cyclopass/cyclopass-api` (amd64 et arm64, donc Mac M1/M2 compris), avec deux tags :

- `X.Y.Z` : la version du fichier [`VERSION`](VERSION). Ce tag est **immuable** : une version publiée n'est jamais écrasée.
- `sha-<commit>` : un tag par commit sur `main`.

Le déploiement se fait **uniquement** depuis le dépôt [`cyclopass-deploy`](https://github.com/cyclopass/cyclopass-deploy) (GitOps).

## Configuration

Toute la configuration passe par des **variables d'environnement**. Aucun secret n'est écrit dans le code. Un exemple est fourni dans [`.env.example`](.env.example).

| Variable | Rôle | Défaut |
|---|---|---|
| `APP_ENV` | `development`, `test`, `staging` ou `production` | `development` |
| `SECRET_KEY` | Clé secrète Flask. **Obligatoire** en staging et en production | clé aléatoire en dev |
| `API_KEYS` | Clés d'API autorisées pour `POST /reservations`, séparées par des virgules. **Obligatoire** en staging et en production | aucune |
| `DATABASE_PATH` | Chemin du fichier SQLite | `cyclopass.db` |
| `METEO_API_URL` | URL de l'API météo | `https://api.meteo.example.com/v1/now` |
| `METEO_API_TOKEN` | Token de l'API météo (envoyé dans un en-tête, jamais dans l'URL) | aucun → `/meteo` répond 503 |
| `METEO_TIMEOUT` | Timeout de l'appel météo, en secondes | `5` |
| `SEED_DEMO_DATA` | Créer les stations de démonstration si la base est vide | `true` |

En staging ou en production, l'application **refuse de démarrer** si `SECRET_KEY` ou `API_KEYS` manquent.

## Routes

| Méthode | Route | Description | Codes |
|---|---|---|---|
| GET | `/health` | Santé de l'application (utilisé par le healthcheck) | 200 |
| GET | `/stations` | Liste des stations | 200 |
| GET | `/recherche?ville=Lille` | Stations d'une ville | 200, 400 |
| POST | `/reservations` | Réserve un vélo. En-tête `X-API-Key` requis. Corps : `{"usager": "...", "station_id": 1}` | 201, 400, 401, 404, 409 |
| GET | `/meteo?ville=Lille` | Météo de la ville | 200, 400, 502, 503 |

Les erreurs sont toujours renvoyées en JSON (`{"erreur": "..."}`), sans détail interne.

## Qualité et sécurité

```bash
flake8                          # style et erreurs
pytest --cov                    # tests + couverture
bandit -r app wsgi.py           # analyse de sécurité du code
```

Les mêmes contrôles tournent automatiquement dans GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) à chaque push et à chaque pull request vers `main`.

## Structure

```
app/            application (factory create_app, configuration, base, routes)
tests/          tests pytest
wsgi.py         point d'entrée du serveur
docs/           audit, politiques, roadmap, KPIs, rapport
```
