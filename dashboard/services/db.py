"""Database helpers for Scraper-Pro dashboard."""
import os
from urllib.parse import quote_plus
import streamlit as st
from sqlalchemy import create_engine, text


def get_db_url() -> str:
    """
    Construit l'URL de connexion PostgreSQL depuis les variables d'environnement.

    Returns:
        URL de connexion PostgreSQL
    """
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "scraper_db")
    user = os.getenv("POSTGRES_USER", "scraper_admin")
    password = os.getenv("POSTGRES_PASSWORD", "")
    return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{db}"


@st.cache_resource
def get_engine():
    """
    Retourne une instance SQLAlchemy Engine avec cache.

    Returns:
        SQLAlchemy Engine
    """
    return create_engine(get_db_url(), pool_pre_ping=True)


def query_df(sql: str, params: dict | None = None):
    """
    Exécute une requête SQL et retourne les résultats sous forme de liste de dicts.

    Args:
        sql: Requête SQL à exécuter
        params: Paramètres de la requête (optionnel)

    Returns:
        Liste de dictionnaires représentant les lignes
    """
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        return [dict(row._mapping) for row in result]


def query_scalar(sql: str, params: dict | None = None):
    """
    Exécute une requête SQL et retourne une seule valeur scalaire.

    Args:
        sql: Requête SQL à exécuter
        params: Paramètres de la requête (optionnel)

    Returns:
        Valeur scalaire (ou 0 si NULL)
    """
    engine = get_engine()
    with engine.connect() as conn:
        return conn.execute(text(sql), params or {}).scalar() or 0
