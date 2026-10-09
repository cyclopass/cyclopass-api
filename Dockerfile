# syntax=docker/dockerfile:1
# ---- Étape 1 : construction des dépendances -------------------------------
FROM python:3.12-slim-trixie AS build

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt \
 && pip uninstall -y pip   # pip n'a rien à faire dans l'image d'exécution

# ---- Étape 2 : image d'exécution, sans outils de build ----------------------
FROM python:3.12-slim-trixie

LABEL org.opencontainers.image.source="https://github.com/cyclopass/cyclopass-api" \
      org.opencontainers.image.description="CycloPass API" \
      org.opencontainers.image.licenses="UNLICENSED"

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    DATABASE_PATH=/app/data/cyclopass.db

# Pas de pip dans l'image d'exécution : ni ses dépendances embarquées
# (signalées par Trivy), ni la possibilité d'installer quoi que ce soit.
RUN python -m pip uninstall -y pip setuptools wheel 2>/dev/null; \
    rm -rf /usr/local/lib/python3.12/ensurepip /usr/local/bin/pip*

# Utilisateur dédié, sans shell ni droits root.
RUN groupadd --system --gid 10001 cyclopass \
 && useradd --system --uid 10001 --gid cyclopass --no-create-home --shell /usr/sbin/nologin cyclopass

WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY app/ app/
COPY wsgi.py VERSION ./
RUN mkdir -p /app/data && chown cyclopass:cyclopass /app/data

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"]

# Serveur de production : jamais app.run() ni mode debug.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "wsgi:app"]
