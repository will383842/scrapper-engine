"""
Warmup guard - checks email-engine quotas before MailWizz injection.

Prevents blowing warmup phases by injecting too many contacts at once.
Queries email-engine's /api/v1/warmup/plans to get current daily quotas,
then limits the number of contacts synced per batch accordingly.

email-engine WarmupPlanResponse fields:
  - phase: str (e.g. "week_1", "week_2", ...)
  - current_daily_quota: int
  - paused: bool
  - bounce_rate_7d: float
  - spam_rate_7d: float
  (no sent_today field — we track usage locally)
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
        is disabled (WARMUP_CHECK_ENABLED=false).
        Returns 0 if email-engine is unreachable (fail-safe: pause sending).
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
            logger.warning(
                f"Email-engine returned {response.status_code}, "
                "pausing sends (fail-safe)"
            )
            return 0

        plans = response.json()
        if not plans:
            # No warmup plans = no restriction
            return None

        # Sum up daily quotas across all active warmup plans
        total_daily_quota = 0

        for plan in plans if isinstance(plans, list) else [plans]:
            # email-engine uses "phase" (e.g. "week_1"), not "status"
            phase = plan.get("phase", "")
            paused = plan.get("paused", False)

            # Skip paused plans
            if paused:
                continue

            # Any plan with a phase is active (phases: week_1..week_6, done)
            if not phase or phase == "done":
                continue

            # email-engine uses "current_daily_quota"
            daily_quota = plan.get("current_daily_quota", 0)
            total_daily_quota += daily_quota

        if total_daily_quota == 0:
            # No active warmup plans (all paused or done) = no limit
            return None

        usable_quota = int(total_daily_quota * QUOTA_USAGE_RATIO)

        logger.info(
            f"Warmup guard: quota={total_daily_quota}, "
            f"usable={usable_quota} ({QUOTA_USAGE_RATIO:.0%})"
        )

        return usable_quota

    except httpx.TimeoutException:
        logger.warning("Email-engine API timeout, pausing sends (fail-safe)")
        return 0
    except Exception as e:
        logger.warning(f"Warmup check failed: {e}, pausing sends (fail-safe)")
        return 0
