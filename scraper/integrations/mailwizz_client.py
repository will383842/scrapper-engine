"""MailWizz API client for subscriber management."""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

# Client cache
_clients: dict[str, "MailWizzClient"] = {}


def get_client(platform: str) -> "MailWizzClient":
    """Get or create MailWizz client for a platform."""
    if platform not in _clients:
        if platform == "sos-expat":
            api_url = os.getenv("MAILWIZZ_SOS_EXPAT_API_URL")
            api_key = os.getenv("MAILWIZZ_SOS_EXPAT_API_KEY")
        elif platform == "ulixai":
            api_url = os.getenv("MAILWIZZ_ULIXAI_API_URL")
            api_key = os.getenv("MAILWIZZ_ULIXAI_API_KEY")
        else:
            raise ValueError(f"Unknown platform: {platform}")

        _clients[platform] = MailWizzClient(api_url, api_key)
    return _clients[platform]


class MailWizzClient:
    """Client for MailWizz REST API."""

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.Client(
            timeout=30.0,
            headers={
                "X-MW-PUBLIC-KEY": api_key,
                "Content-Type": "application/json",
            },
        )

    def add_subscriber(
        self, list_id: int, data: dict, tags: list[str] | None = None
    ) -> dict:
        """Add a subscriber to a MailWizz list."""
        endpoint = f"{self.api_url}/lists/{list_id}/subscribers"

        payload = data.copy()
        if tags:
            payload["tags"] = ",".join(tags)

        try:
            response = self.client.post(endpoint, json=payload)
            result = response.json()

            if response.status_code == 201:
                sub_uid = result.get("data", {}).get("record", {}).get("subscriber_uid")
                logger.info(
                    f"Subscriber added: {data.get('EMAIL')} -> list #{list_id} "
                    f"(UID: {sub_uid})"
                )
                return {"success": True, "subscriber_uid": sub_uid}

            error = result.get("error", f"HTTP {response.status_code}")
            logger.error(f"MailWizz error: {error}")
            return {"success": False, "error": error}

        except Exception as e:
            logger.error(f"MailWizz exception: {e}")
            return {"success": False, "error": str(e)}

    def get_subscriber(self, list_id: int, email: str) -> dict | None:
        """Find subscriber by email."""
        endpoint = f"{self.api_url}/lists/{list_id}/subscribers/search-by-email"
        try:
            response = self.client.get(endpoint, params={"EMAIL": email})
            if response.status_code == 200:
                return response.json().get("data", {}).get("record")
            return None
        except Exception as e:
            logger.error(f"MailWizz search error: {e}")
            return None

    def update_subscriber(
        self, list_id: int, subscriber_uid: str, data: dict
    ) -> bool:
        """Update an existing subscriber."""
        endpoint = f"{self.api_url}/lists/{list_id}/subscribers/{subscriber_uid}"
        try:
            response = self.client.put(endpoint, json=data)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"MailWizz update error: {e}")
            return False
