"""HMAC authentication middleware for the API."""

import hashlib
import hmac
import os
import time

from fastapi import HTTPException, Request


async def verify_hmac(request: Request):
    """Verify HMAC-SHA256 signature on incoming API requests."""
    secret = os.getenv("API_HMAC_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail="API secret not configured")

    signature = request.headers.get("X-Signature")
    timestamp = request.headers.get("X-Timestamp")

    if not signature or not timestamp:
        raise HTTPException(status_code=401, detail="Missing signature headers")

    # Reject if timestamp is older than 5 minutes
    try:
        ts = int(timestamp)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid timestamp")

    if abs(time.time() - ts) > 300:
        raise HTTPException(status_code=401, detail="Request expired")

    # Read body
    body = await request.body()
    body_str = body.decode("utf-8") if body else ""

    # Verify signature
    message = f"{timestamp}.{body_str}"
    expected = hmac.new(
        secret.encode(), message.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid signature")
