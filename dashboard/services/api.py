"""API client for Scraper-Pro dashboard."""
import hashlib
import hmac
import json
import os
import time
import requests


SCRAPER_API_URL = os.getenv("SCRAPER_API_URL", "http://scraper:8000")
API_HMAC_SECRET = os.getenv("API_HMAC_SECRET", "")


def api_request(method: str, path: str, json_data: dict | None = None) -> dict:
    """
    Effectue une requête HMAC-signée vers l'API scraper.

    Args:
        method: Méthode HTTP (GET, POST, etc.)
        path: Chemin de l'endpoint (ex: "/api/v1/scraping/jobs")
        json_data: Données JSON à envoyer (optionnel)

    Returns:
        Réponse JSON de l'API

    Raises:
        requests.exceptions.HTTPError: Si la requête échoue
    """
    url = f"{SCRAPER_API_URL}{path}"
    ts = str(int(time.time()))
    body_str = json.dumps(json_data) if json_data else ""

    # Générer signature HMAC
    sig = hmac.new(
        API_HMAC_SECRET.encode(),
        f"{ts}.{body_str}".encode(),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "X-Signature": sig,
        "X-Timestamp": ts,
        "Content-Type": "application/json",
    }

    resp = requests.request(method, url, headers=headers, json=json_data, timeout=30)
    resp.raise_for_status()
    return resp.json()
