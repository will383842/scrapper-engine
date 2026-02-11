"""
Warmup guard - checks email-engine quotas before MailWizz injection.

Prevents blowing warmup phases by injecting too many contacts at once.
Queries email-engine's /api/v1/warmup/plans to get current daily quotas,
then limits the number of contacts synced per batch accordingly.
"""

import logging
import os
from datetime import date

import httpx

logger = logging.getLogger(__name__)

# How much of the daily quota we allow the scraper to consume (leave room for manual sends)
QUOTA_USAGE_RATIO = float(os.getenv("WARMUP_QUOTA_USAGE_RATIO", "0.8"))


def get_daily_quota_remaining() -> int | None:
    """
    Query email-engine API to get the remaining daily sending quota.

    Returns:
        Number of emails we can still inject today, or None if warmup check
        is disabled or unreachable (in which case, proceed without limit).
    """
    enabled = os.getenv("WARMUP_CHECK_ENABLED", "false").lower() == "true"
    if not enabled:
        return None

    api_url = os.getenv("EMAIL_ENGINE_API_URL", "").rstrip("/")
    api_key = os.getenv("EMAIL_ENGINE_API_KEY", "")

    if not api_url:
        logger.debug("EMAIL_ENGINE_API_URL not set, skipping warmup check")
        return None

    try:
        response = httpx.get(
            f"{api_url}/api/v1/warmup/plans",
            headers={"X-API-Key": api_key} if api_key else {},
            timeout=10.0,
        )

        if response.status_code != 200:
            logger.warning(f"Email-engine returned {response.status_code}, skipping warmup check")
            return None

        plans = response.json()
        if not plans:
            return None

        # Sum up daily quotas across all active warmup plans
        total_daily_quota = 0
        total_sent_today = 0

        for plan in plans if isinstance(plans, list) else [plans]:
            status = plan.get("status", "")
            if status not in ("active", "warming"):
                continue

            daily_quota = plan.get("daily_quota", 0) or plan.get("current_quota", 0)
            sent_today = plan.get("sent_today", 0)
            total_daily_quota += daily_quota
            total_sent_today += sent_today

        if total_daily_quota == 0:
            # No active warmup = no limit
            return None

        usable_quota = int(total_daily_quota * QUOTA_USAGE_RATIO)
        remaining = max(0, usable_quota - total_sent_today)

        logger.info(
            f"Warmup guard: quota={total_daily_quota}, "
            f"usable={usable_quota} ({QUOTA_USAGE_RATIO:.0%}), "
            f"sent_today={total_sent_today}, remaining={remaining}"
        )

        return remaining

    except httpx.TimeoutException:
        logger.warning("Email-engine API timeout, skipping warmup check")
        return None
    except Exception as e:
        logger.warning(f"Warmup check failed: {e}, proceeding without limit")
        return None
