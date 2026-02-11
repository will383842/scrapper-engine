"""Send webhook notifications to SOS-Expat and Ulixai."""

import hashlib
import hmac
import json
import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

PLATFORM_CONFIGS = {
    "sos-expat": {
        "url_env": "WEBHOOK_SOS_EXPAT_URL",
        "secret_env": "WEBHOOK_SOS_EXPAT_SECRET",
    },
    "ulixai": {
        "url_env": "WEBHOOK_ULIXAI_URL",
        "secret_env": "WEBHOOK_ULIXAI_SECRET",
    },
}


def _sign_payload(secret: str, timestamp: str, body: str) -> str:
    """Generate HMAC-SHA256 signature."""
    message = f"{timestamp}.{body}"
    return hmac.new(
        secret.encode(), message.encode(), hashlib.sha256
    ).hexdigest()


def send_webhook(platform: str, event_type: str, data: dict) -> bool:
    """
    Send webhook event to a platform.

    Args:
        platform: 'sos-expat' or 'ulixai'
        event_type: 'bounce', 'open', 'click', 'unsubscribe'
        data: event payload
    """
    config = PLATFORM_CONFIGS.get(platform)
    if not config:
        logger.warning(f"Unknown platform for webhook: {platform}")
        return False

    url = os.getenv(config["url_env"])
    secret = os.getenv(config["secret_env"])

    if not url or not secret:
        logger.debug(f"Webhook not configured for {platform}")
        return False

    payload = {
        "event_type": event_type,
        "platform": platform,
        "timestamp": int(time.time()),
        **data,
    }

    body = json.dumps(payload, sort_keys=True)
    timestamp = str(int(time.time()))
    signature = _sign_payload(secret, timestamp, body)

    try:
        response = httpx.post(
            url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Timestamp": timestamp,
                "X-Signature": signature,
            },
            timeout=10.0,
        )

        if response.status_code == 200:
            logger.info(f"Webhook sent: {event_type} -> {platform}")
            return True

        logger.warning(
            f"Webhook failed: {platform} returned {response.status_code}"
        )
        return False

    except Exception as e:
        logger.error(f"Webhook error for {platform}: {e}")
        return False
