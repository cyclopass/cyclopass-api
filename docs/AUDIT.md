# Audit de l'existant — CycloPass legacy (2019)

> Périmètre : dossier `cyclopass-legacy/` tel que laissé par Julien (`app.py`, `requirements.txt`, `LISEZMOI.txt`).
> Date : 09/10/2026 — Auditeur : Thomas (PO / Security Champion / Ops).

## Méthode

1. **Lecture manuelle** du code et du `LISEZMOI.txt`, sans outil, pour lister les failles « à l'œil ».
2. **Exécution** de l'application (venv Python, `pip install -r requirements.txt`, `python app.py`) et **reproduction** de chaque faille avec des requêtes HTTP.
3. **Confirmation outillée** seulement après : `bandit` (analyse statique du code) et `pip-audit` (vulnérabilités connues des dépendances).

La colonne « Outil ? » indique si un outil automatique a aussi trouvé le problème. Cette colonne sert à répondre à la question de synthèse n°1 du rapport final.

Échelle de gravité :

| Gravité | Signification |
|---|---|
| 🔴 Critique | Exploitable à distance sans authentification, avec un impact majeur (fuite de données, exécution de code). À corriger avant toute mise en ligne. |
| 🟠 Haute | Impact fort ou exploitation facile. À corriger dans le sprint. |
| 🟡 Moyenne | Impact limité ou conditions particulières. À planifier. |
| 🟢 Faible | Mauvaise pratique sans impact direct. |

---

## 1. Problèmes de reproductibilité

| # | Problème | Constat | Gravité | Pratique DevOps qui y répond |
|---|---|---|---|---|
| R1 | **Version de Python non spécifiée** | Ni le `LISEZMOI.txt` ni aucun fichier n'indique la version de Python attendue. Le code tourne aujourd'hui en 3.13 « par chance ». | 🟡 Moyenne | Version figée dans le `Dockerfile` (`python:3.12-slim`) et dans la CI. |
| R2 | **Dépendances figées en 2019, transitives non figées** | Seules 3 librairies sont épinglées. Leurs dépendances (`urllib3`, `idna`, `Jinja2`, `click`…) prennent la version du jour : deux installations à 6 mois d'écart n'ont pas le même code. | 🟠 Haute | `requirements.txt` à jour et complet, séparé de `requirements-dev.txt`, avec mise à jour suivie (Dependabot) et contrôlée (pip-audit). |
| R3 | **Documentation quasi inexistante** | `LISEZMOI.txt` = « Pour lancer : python app.py ». Pas d'environnement virtuel, pas de liste des routes, pas de configuration. | 🟠 Haute | `README.md` qui permet à un nouvel arrivant de lancer l'app sans aide (testé dans un environnement vierge). |
| R4 | **Initialisation de la base cachée dans le `__main__`** | `init_db()` n'est appelée que si on lance `python app.py`. Avec un vrai serveur (gunicorn), la table n'existe pas → erreur 500. La base est créée dans le dossier courant. | 🟡 Moyenne | Factory `create_app()` qui initialise la base, chemin configurable (`DATABASE_PATH`). |
| R5 | **Configuration écrite dans le code** | Clé secrète, token, port, mode debug : tout est en dur. Impossible d'avoir un comportement différent en dev, staging et prod sans modifier le code. | 🟠 Haute | Configuration par variables d'environnement (12-factor), fichier `config.env` versionné dans le dépôt de déploiement. |
| R6 | **Pas d'artefact de livraison** | On copie un fichier `app.py` à la main. On ne sait jamais quelle version tourne en prod. | 🟠 Haute | Image Docker versionnée (`VERSION`), publiée dans un registre, déployée en GitOps. |

---

## 2. Problèmes de sécurité dans le code

Trouvés à la main, puis reproduits sur l'application lancée. **10 failles de sécurité et 3 bugs métier.**

| # | Faille | Où | Preuve (reproduite) | Gravité | Outil ? | Pratique DevSecOps |
|---|---|---|---|---|---|---|
| S1 | **Injection SQL** (CWE-89) — c'est la « recherche bizarre » du client | `/recherche`, ligne 46 : `"... WHERE ville = '%s'" % ville` | `GET /recherche?ville=x' OR '1'='1` → **les 3 stations de toutes les villes**. `ville=O'Brien` → erreur 500. | 🔴 Critique | bandit B608 | Requêtes paramétrées, test de non-régression dédié, SAST (bandit) bloquant en CI, revue de code. |
| S2 | **Mode debug activé** (CWE-489) | `app.run(..., debug=True)` | La console Werkzeug est active : elle permet d'exécuter du Python sur le serveur (le PIN de protection peut être reconstitué). Les stack traces complètes sont affichées aux clients. | 🔴 Critique dès que c'est exposé | bandit B201 | Configuration par environnement, serveur de production (gunicorn) dans un conteneur, jamais `app.run` en prod. |
| S3 | **Secrets en dur dans le code** (CWE-798) | `app.config["SECRET_KEY"]` et `METEO_API_TOKEN` (préfixe `mt_live_`), valeurs en clair dans `app.py` | Lisibles par quiconque a le code. Un token `live` = production. Ils sont aussi **dans l'historique Git** dès qu'on versionne. | 🟠 Haute | bandit B105 (×2), gitleaks | Variables d'environnement et secrets CI, gitleaks dans le pipeline, **rotation** des secrets exposés, nettoyage de l'historique. |
| S4 | **Vérification TLS désactivée** (CWE-295) | `/meteo` : `requests.get(..., verify=False)` | N'importe quel intermédiaire réseau peut se faire passer pour l'API météo et **récupérer le token** (envoyé dans la requête). | 🟠 Haute | bandit B501 | TLS toujours vérifié. Contrôle SAST bloquant. |
| S5 | **Token transmis dans l'URL** (CWE-598) | `params={"token": METEO_API_TOKEN}` | Les tokens dans l'URL finissent dans les logs des proxys et des serveurs. | 🟡 Moyenne | ❌ non | Token dans un en-tête HTTP (`Authorization`). Revue de code. |
| S6 | **Appel externe sans timeout** (CWE-400) | `/meteo` | Si l'API météo ne répond plus, chaque requête bloque un worker indéfiniment → toute l'API tombe. | 🟡 Moyenne | bandit B113 | Timeout systématique, gestion d'erreur (502), monitoring. |
| S7 | **Aucune authentification sur l'écriture** (CWE-306) | `POST /reservations` | N'importe qui sur Internet peut réserver au nom de n'importe quel usager et **vider toutes les stations** en boucle. Bloquant pour l'ouverture aux partenaires. | 🟠 Haute | ❌ non | Clé d'API par partenaire (puis OAuth2), rate limiting, modélisation des menaces avant ouverture. |
| S8 | **Aucune validation des entrées** (CWE-20) | `POST /reservations` : `data["usager"]` | Un JSON vide ou mal formé → `KeyError` → 500, avec la stack trace complète en mode debug (fuite d'information). | 🟡 Moyenne | ❌ non | Validation systématique, gestionnaires d'erreurs JSON sans détail interne, tests des cas invalides. |
| S9 | **Dépendances vulnérables** (CWE-1104) | `requirements.txt` | `pip-audit` : **25 vulnérabilités connues** (Werkzeug 10, urllib3 7, requests 4, Flask 2, idna 2). | 🟠 Haute | pip-audit | SCA (pip-audit) en gate bloquant, Dependabot, politique de mise à jour. |
| S10 | **Réponse tierce relayée telle quelle** | `/meteo` : `return jsonify(r.json())` | Tout ce que renvoie l'API météo est transmis aux clients sans contrôle. Si elle répond autre chose que du JSON → 500. Le paramètre `ville` est transmis sans validation. | 🟢 Faible | ❌ non | Valider les entrées, filtrer la réponse, gérer les erreurs de l'API tierce. |

### Bugs métier (intégrité des données)

| # | Bug | Preuve (reproduite) | Gravité | Outil ? | Pratique |
|---|---|---|---|---|---|
| B1 | **Stock de vélos négatif** | 15 réservations sur « Grand Place » (4 vélos) → toutes acceptées, stock = **-11**. | 🟠 Haute | ❌ non | Règle métier testée (`velos > 0`), mise à jour atomique (`UPDATE … WHERE velos > 0`). |
| B2 | **Réservation sur une station inexistante acceptée** | `{"usager": "a", "station_id": 999}` → **201 « Vélo réservé »**. | 🟡 Moyenne | ❌ non | Vérifier l'existence (404), contraintes en base, tests. |
| B3 | **Réservation non atomique** | Insertion puis décrément sans vérification : deux requêtes simultanées peuvent prendre le dernier vélo. | 🟡 Moyenne | ❌ non | Décrément conditionnel et vérification du nombre de lignes modifiées dans une seule transaction. |

**Bilan outils :** bandit et pip-audit détectent S1, S2, S3, S4, S6 et S9. **Aucun outil n'a détecté S5, S7, S8, S10, B1, B2 et B3**, soit plus de la moitié des problèmes, dont l'absence totale d'authentification et le stock négatif. Ce sont des failles de logique métier, que seule une personne qui comprend ce que l'application doit faire peut voir.

---

## 3. Problèmes de processus

Source : `LISEZMOI.txt`, section « Mise en production (procédure de Julien, à faire le vendredi soir) ».

| # | Problème | Constat | Gravité | Pratique DevOps / DevSecOps |
|---|---|---|---|---|
| P1 | **Mise en production manuelle en SSH** | `scp app.py`, `pip install` « si ça plante », `nohup python app.py`. Chaque déploiement est unique et non reproductible. | 🔴 Critique | Pipeline CI/CD et déploiement GitOps depuis un dépôt `cyclopass-deploy`. |
| P2 | **Mot de passe de prod dans un carnet papier** | « mot de passe dans le carnet du bureau » : partagé, jamais changé, sans trace de qui s'en sert. | 🟠 Haute | Plus aucun accès humain direct à la prod. Secrets gérés par la plateforme (GitHub Secrets) et accès nominatifs. |
| P3 | **Déploiement le vendredi soir** | Le moment où il y a le moins de monde pour réparer. | 🟡 Moyenne | Déploiements petits et fréquents, automatisés, à n'importe quel moment de la semaine. |
| P4 | **Coupure brutale (`kill -9`)** | Les requêtes en cours sont perdues, et on ne vérifie pas que la nouvelle version démarre. | 🟡 Moyenne | Conteneur avec healthcheck (`/health`), redémarrage géré par l'orchestrateur. |
| P5 | **Pas de rollback** | « remettre l'ancien fichier (s'il a été gardé) ». | 🟠 Haute | Images versionnées et immuables : un rollback = `git revert` dans `cyclopass-deploy`. |
| P6 | **Aucun test, aucune recette** | « Pas de tests. Pas de recette. » | 🟠 Haute | Tests automatisés (pytest) exécutés à chaque push, couverture mesurée, quality gate. |
| P7 | **Connaissance concentrée sur une personne** (bus factor = 1) | « Si un client appelle, prévenir Julien ». Julien est parti : plus personne ne sait comment ça marche. | 🔴 Critique | Code versionné, documentation à jour, revue de code obligatoire, rôles partagés (voir `EQUIPE.md`). |
| P8 | **Pas de versionnement ni de traçabilité** | Le code nous arrive en zip, sans historique Git ni numéro de version : impossible de savoir ce qui tourne en prod ni ce qui a changé. | 🟠 Haute | Git + pull requests + fichier `VERSION` + tags d'image. |
| P9 | **Pas de supervision** | On apprend qu'il y a un problème quand un client appelle. | 🟠 Haute | Métriques Prometheus, tableau de bord Grafana, alertes. |
| P10 | **Pas de processus de signalement des failles** | Le client qui a trouvé l'injection SQL n'avait aucun canal pour la signaler. | 🟡 Moyenne | `SECURITY_POLICY.md` avec délais de traitement selon la criticité. |

---

## 4. Synthèse et priorités

**Verdict : l'application ne doit pas être exposée en l'état**, et encore moins ouverte à des partenaires. Deux failles critiques (S1, S2) sont exploitables par n'importe qui en une requête.

Ordre de traitement retenu :

1. **Tout de suite** : S1 (injection), S2 (debug), S3 (secrets + rotation), S4/S6 (appel météo), B1/B2 (stock). → Étape 2 (refactor + tests).
2. **Dans la foulée** : S9 (dépendances) → gate pip-audit (étape 4). R6/P1/P5 → Docker + GitOps (étape 3).
3. **Avant l'ouverture aux partenaires** : S7 (authentification), rate limiting, supervision (P9), processus (P7, P10). → Roadmap J+30 / J+60 / J+90.
