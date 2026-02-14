# Dockerfile pour Dashboard Scraper-Pro MODE 2
FROM python:3.11-slim

# Métadonnées
LABEL maintainer="Scraper-Pro Team"
LABEL description="Dashboard MODE 2 - Streamlit avec i18n FR/EN"
LABEL version="2.0.0"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Répertoire de travail
WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier requirements et installer les packages Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier UNIQUEMENT le code de l'application dashboard
# Pas besoin de config/ car tout passe par env vars
COPY . .

# Créer un utilisateur non-root pour la sécurité
RUN useradd -m -u 1000 streamlit && \
    chown -R streamlit:streamlit /app

# Passer à l'utilisateur non-root
USER streamlit

# Exposer le port Streamlit
EXPOSE 8501

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Commande de démarrage
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=true"]
