"""
SerpAPI fallback client for when Google blocks with CAPTCHA/403.

SerpAPI handles Google's anti-bot measures and returns structured results.
Used as fallback only when direct scraping fails.
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

SERPAPI_BASE = "https://serpapi.com/search"


def is_available() -> bool:
    """Check if SerpAPI is configured."""
    return bool(os.getenv("SERPAPI_KEY"))


def search_google(query: str, country: str | None = None,
                  language: str | None = None, start: int = 0,
                  num: int = 10) -> list[dict]:
    """
    Search Google via SerpAPI.

    Returns list of organic results with keys: link, title, snippet.
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return []

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "start": start,
        "num": num,
    }
    if country:
        params["gl"] = country
    if language:
        params["hl"] = language
        params["lr"] = f"lang_{language}"

    try:
        response = httpx.get(SERPAPI_BASE, params=params, timeout=30.0)
        if response.status_code != 200:
            logger.warning(f"SerpAPI returned {response.status_code}")
            return []

        data = response.json()
        results = []
        for item in data.get("organic_results", []):
            results.append({
                "link": item.get("link", ""),
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
            })
        return results

    except Exception as e:
        logger.error(f"SerpAPI error: {e}")
        return []


def search_google_maps(query: str, location: str | None = None,
                       language: str | None = None) -> list[dict]:
    """
    Search Google Maps via SerpAPI.

    Returns list of local results with keys: title, address, phone, website, link.
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return []

    params = {
        "engine": "google_maps",
        "q": query,
        "api_key": api_key,
        "type": "search",
    }
    if location:
        params["q"] = f"{query} {location}"
    if language:
        params["hl"] = language

    try:
        response = httpx.get(SERPAPI_BASE, params=params, timeout=30.0)
        if response.status_code != 200:
            logger.warning(f"SerpAPI Maps returned {response.status_code}")
            return []

        data = response.json()
        results = []
        for item in data.get("local_results", []):
            results.append({
                "title": item.get("title", ""),
                "address": item.get("address", ""),
                "phone": item.get("phone", ""),
                "website": item.get("website", ""),
                "link": item.get("website") or item.get("link", ""),
            })
        return results

    except Exception as e:
        logger.error(f"SerpAPI Maps error: {e}")
        return []
