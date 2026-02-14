"""
Cron job: Sync validated contacts to MailWizz via API.
Runs every hour (offset 30 min from process_contacts).
"""

import json
import logging
import sys

from scraper.database import get_db_session
from sqlalchemy import text
from scraper.integrations.mailwizz_client import get_client
from scraper.integrations.warmup_guard import get_daily_quota_remaining

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("sync_to_mailwizz")

BATCH_SIZE = 100
MAX_RETRIES = 3


def sync_contacts_to_mailwizz():
    """Send validated contacts to MailWizz lists, respecting warmup quotas."""
    stats = {"success": 0, "failed": 0, "retries": 0, "held_warmup": 0}

    # Check warmup quota before syncing
    quota_remaining = get_daily_quota_remaining()
    effective_limit = BATCH_SIZE

    if quota_remaining is not None:
        if quota_remaining <= 0:
            logger.info("Warmup quota exhausted for today, skipping sync")
            return stats
        effective_limit = min(BATCH_SIZE, quota_remaining)
        logger.info(f"Warmup guard: limiting batch to {effective_limit} contacts")

    with get_db_session() as session:
        # Lock rows to prevent concurrent sync jobs from processing the same contacts
        contacts = session.execute(
            text("""
            SELECT * FROM validated_contacts
            WHERE status = 'ready_for_mailwizz'
            AND retry_count < :max_retries
            ORDER BY created_at ASC
            LIMIT :limit
            FOR UPDATE SKIP LOCKED
            """),
            {"max_retries": MAX_RETRIES, "limit": effective_limit},
        ).mappings().all()

        logger.info(f"Syncing {len(contacts)} contacts to MailWizz...")

        for contact in contacts:
            contact = dict(contact)

            # Use savepoint so one contact's failure doesn't roll back the whole batch
            savepoint = session.begin_nested()
            try:
                client = get_client(contact["platform"])

                # Prepare subscriber data
                name_parts = (contact.get("name") or "").split()
                subscriber_data = {
                    "EMAIL": contact["email"],
                    "FNAME": name_parts[0] if name_parts else "",
                    "LNAME": name_parts[-1] if len(name_parts) > 1 else "",
                    "COUNTRY": contact.get("country", ""),
                    "PHONE": contact.get("phone", ""),
                    "WEBSITE": contact.get("website", ""),
                    "CATEGORY": contact["category"],
                    "SOURCE": "scraping_auto",
                }

                # Add social media fields
                social = contact.get("social_media")
                if social:
                    if isinstance(social, str):
                        social = json.loads(social)
                    subscriber_data["FACEBOOK"] = social.get("facebook", "")
                    subscriber_data["INSTAGRAM"] = social.get("instagram", "")
                    subscriber_data["LINKEDIN"] = social.get("linkedin", "")

                # Tags
                tags = contact.get("tags")
                if isinstance(tags, str):
                    tags = json.loads(tags)

                # Send to MailWizz
                result = client.add_subscriber(
                    list_id=contact["mailwizz_list_id"],
                    data=subscriber_data,
                    tags=tags,
                )

                if result["success"]:
                    session.execute(
                        text("""
                        UPDATE validated_contacts
                        SET status = 'sent_to_mailwizz',
                            mailwizz_subscriber_id = :sub_id,
                            sent_to_mailwizz_at = NOW(),
                            updated_at = NOW()
                        WHERE id = :id
                        """),
                        {"sub_id": result.get("subscriber_uid"), "id": contact["id"]},
                    )

                    session.execute(
                        text("""
                        INSERT INTO mailwizz_sync_log
                            (contact_id, platform, list_id, status, response)
                        VALUES (:cid, :platform, :list_id, 'success', :response)
                        """),
                        {
                            "cid": contact["id"],
                            "platform": contact["platform"],
                            "list_id": contact["mailwizz_list_id"],
                            "response": json.dumps(result),
                        },
                    )

                    savepoint.commit()
                    stats["success"] += 1
                    logger.info(f"Synced: {contact['email']} -> {contact['platform']}")

                else:
                    retry_count = contact["retry_count"] + 1
                    new_status = "failed" if retry_count >= MAX_RETRIES else "ready_for_mailwizz"

                    session.execute(
                        text("""
                        UPDATE validated_contacts
                        SET status = :status,
                            retry_count = :retry,
                            last_error = :error,
                            updated_at = NOW()
                        WHERE id = :id
                        """),
                        {
                            "status": new_status,
                            "retry": retry_count,
                            "error": result.get("error", "Unknown"),
                            "id": contact["id"],
                        },
                    )

                    session.execute(
                        text("""
                        INSERT INTO mailwizz_sync_log
                            (contact_id, platform, list_id, status, response)
                        VALUES (:cid, :platform, :list_id, 'failed', :response)
                        """),
                        {
                            "cid": contact["id"],
                            "platform": contact["platform"],
                            "list_id": contact["mailwizz_list_id"],
                            "response": json.dumps(result),
                        },
                    )

                    savepoint.commit()

                    if new_status == "failed":
                        stats["failed"] += 1
                        logger.error(f"Failed permanently: {contact['email']}")
                    else:
                        stats["retries"] += 1
                        logger.warning(
                            f"Retry {retry_count}/{MAX_RETRIES}: {contact['email']}"
                        )

            except Exception as exc:
                savepoint.rollback()
                stats["failed"] += 1
                logger.error(f"Exception syncing {contact.get('email')}: {exc}")

    logger.info(f"Sync complete: {stats}")
    return stats


if __name__ == "__main__":
    try:
        sync_contacts_to_mailwizz()
    except Exception as e:
        logger.critical(f"MailWizz sync job crashed: {e}", exc_info=True)
        sys.exit(1)
