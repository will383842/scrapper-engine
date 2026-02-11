"""API routes for contact management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from scraper.api.auth import verify_hmac
from scraper.api.schemas import BounceFeedbackRequest, DeliveryFeedbackRequest
from scraper.database import get_db_session

router = APIRouter()


@router.get("/stats", dependencies=[Depends(verify_hmac)])
async def get_contacts_stats():
    """Get scraping and contact statistics."""
    with get_db_session() as session:
        scraped = session.execute(
            text("SELECT COUNT(*) as total FROM scraped_contacts")
        ).scalar()
        validated = session.execute(
            text("SELECT COUNT(*) as total FROM validated_contacts")
        ).scalar()
        sent = session.execute(
            text("SELECT COUNT(*) FROM validated_contacts WHERE status = 'sent_to_mailwizz'")
        ).scalar()
        pending = session.execute(
            text("SELECT COUNT(*) FROM validated_contacts WHERE status = 'ready_for_mailwizz'")
        ).scalar()
        bounced = session.execute(
            text("SELECT COUNT(*) FROM validated_contacts WHERE status = 'bounced'")
        ).scalar()

        # Per platform
        by_platform = session.execute(
            text("""
            SELECT platform, category, COUNT(*) as count
            FROM validated_contacts
            GROUP BY platform, category
            ORDER BY platform, count DESC
            """)
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
async def bounce_feedback(payload: BounceFeedbackRequest):
    """
    Receive bounce feedback from MailWizz.
    Marks contact as bounced and updates domain blacklist.
    """
    email = payload.email.lower().strip()
    bounce_type = payload.bounce_type

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email address required")

    domain = email.split("@")[1]
    if not domain:
        raise HTTPException(status_code=400, detail="Invalid email domain")

    with get_db_session() as session:
        # Mark contact as bounced
        session.execute(
            text("""
            UPDATE validated_contacts
            SET status = 'bounced', updated_at = NOW()
            WHERE email = :email
            """),
            {"email": email},
        )

        # Update domain bounce stats (only increment bounce_count, not total_sent)
        session.execute(
            text("""
            INSERT INTO email_domain_blacklist (domain, bounce_count, total_sent, bounce_rate)
            VALUES (:domain, 1, 1, 100.0)
            ON CONFLICT (domain) DO UPDATE SET
                bounce_count = email_domain_blacklist.bounce_count + 1,
                bounce_rate = CASE
                    WHEN email_domain_blacklist.total_sent > 0
                    THEN LEAST(
                        (email_domain_blacklist.bounce_count + 1)::decimal
                        / email_domain_blacklist.total_sent * 100,
                        100.0
                    )
                    ELSE 100.0
                END
            """),
            {"domain": domain},
        )

    return {"status": "ok", "email": email, "bounce_type": bounce_type}


@router.post("/delivery-feedback", dependencies=[Depends(verify_hmac)])
async def delivery_feedback(payload: DeliveryFeedbackRequest):
    """
    Receive delivery confirmation from MailWizz/email-engine.
    Tracks total_sent per domain to calculate accurate bounce rates.
    """
    domain = payload.domain.lower().strip()

    if not domain or "." not in domain:
        raise HTTPException(status_code=400, detail="Valid domain required")

    with get_db_session() as session:
        session.execute(
            text("""
            INSERT INTO email_domain_blacklist (domain, bounce_count, total_sent, bounce_rate)
            VALUES (:domain, 0, :count, 0.0)
            ON CONFLICT (domain) DO UPDATE SET
                total_sent = email_domain_blacklist.total_sent + :count,
                bounce_rate = CASE
                    WHEN (email_domain_blacklist.total_sent + :count) > 0
                    THEN email_domain_blacklist.bounce_count::decimal
                        / (email_domain_blacklist.total_sent + :count) * 100
                    ELSE 0.0
                END
            """),
            {"domain": domain, "count": payload.count},
        )

    return {"status": "ok", "domain": domain, "delivered": payload.count}
