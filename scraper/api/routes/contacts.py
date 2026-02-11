"""API routes for contact management."""

from fastapi import APIRouter, Depends

from scraper.api.auth import verify_hmac
from scraper.database import get_db_session

router = APIRouter()


@router.get("/stats", dependencies=[Depends(verify_hmac)])
async def get_contacts_stats():
    """Get scraping and contact statistics."""
    with get_db_session() as session:
        scraped = session.execute(
            "SELECT COUNT(*) as total FROM scraped_contacts"
        ).scalar()
        validated = session.execute(
            "SELECT COUNT(*) as total FROM validated_contacts"
        ).scalar()
        sent = session.execute(
            "SELECT COUNT(*) FROM validated_contacts WHERE status = 'sent_to_mailwizz'"
        ).scalar()
        pending = session.execute(
            "SELECT COUNT(*) FROM validated_contacts WHERE status = 'ready_for_mailwizz'"
        ).scalar()
        bounced = session.execute(
            "SELECT COUNT(*) FROM validated_contacts WHERE status = 'bounced'"
        ).scalar()

        # Per platform
        by_platform = session.execute(
            """
            SELECT platform, category, COUNT(*) as count
            FROM validated_contacts
            GROUP BY platform, category
            ORDER BY platform, count DESC
            """
        ).mappings().all()

    return {
        "total_scraped": scraped,
        "total_validated": validated,
        "sent_to_mailwizz": sent,
        "pending_sync": pending,
        "bounced": bounced,
        "by_platform": [dict(r) for r in by_platform],
    }


@router.post("/bounce-feedback", dependencies=[Depends(verify_hmac)])
async def bounce_feedback(payload: dict):
    """
    Receive bounce feedback from MailWizz.
    Marks contact as bounced and updates domain blacklist.
    """
    email = payload.get("email", "").lower().strip()
    bounce_type = payload.get("bounce_type", "hard")

    if not email:
        return {"error": "email required"}

    with get_db_session() as session:
        # Mark contact as bounced
        session.execute(
            """
            UPDATE validated_contacts
            SET status = 'bounced', updated_at = NOW()
            WHERE email = :email
            """,
            {"email": email},
        )

        # Update domain bounce stats
        domain = email.split("@")[1]
        session.execute(
            """
            INSERT INTO email_domain_blacklist (domain, bounce_count, total_sent, bounce_rate)
            VALUES (:domain, 1, 1, 100.0)
            ON CONFLICT (domain) DO UPDATE SET
                bounce_count = email_domain_blacklist.bounce_count + 1,
                bounce_rate = (
                    (email_domain_blacklist.bounce_count + 1)::decimal
                    / GREATEST(email_domain_blacklist.total_sent, 1) * 100
                )
            """,
            {"domain": domain},
        )

    return {"status": "ok", "email": email, "bounce_type": bounce_type}
