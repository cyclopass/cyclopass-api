"""Configuration de l'application, lue exclusivement depuis l'environnement."""
import os
import secrets

ENVIRONNEMENTS_DEPLOYES = {"staging", "production"}


class ConfigurationError(RuntimeError):
    """Configuration incomplète ou dangereuse pour l'environnement demandé."""


def charger_config(surcharges=None):
    """Construit la configuration à partir des variables d'environnement.

    En staging et en production, les secrets sont obligatoires : on refuse
    de démarrer plutôt que de tourner avec une valeur par défaut.
    """
    env = os.environ
    app_env = env.get("APP_ENV", "development")

    config = {
        "APP_ENV": app_env,
        "SECRET_KEY": env.get("SECRET_KEY"),
        "DATABASE_PATH": env.get("DATABASE_PATH", "cyclopass.db"),
        "METEO_API_URL": env.get("METEO_API_URL", "https://api.meteo.example.com/v1/now"),
        "METEO_API_TOKEN": env.get("METEO_API_TOKEN"),
        "METEO_TIMEOUT": float(env.get("METEO_TIMEOUT", "5")),
        "API_KEYS": _liste(env.get("API_KEYS", "")),
        "SEED_DEMO_DATA": env.get("SEED_DEMO_DATA", "true").lower() == "true",
        "DEBUG": False,
    }
    if surcharges:
        config.update(surcharges)

    if config["APP_ENV"] in ENVIRONNEMENTS_DEPLOYES:
        manquants = [cle for cle in ("SECRET_KEY", "API_KEYS") if not config[cle]]
        if manquants:
            raise ConfigurationError(
                f"Variables obligatoires en {config['APP_ENV']} : {', '.join(manquants)}"
            )
    elif not config["SECRET_KEY"]:
        # En développement et en test : clé éphémère, jamais une valeur en dur.
        config["SECRET_KEY"] = secrets.token_hex(32)

    return config


def _liste(valeur):
    return [element.strip() for element in valeur.split(",") if element.strip()]
