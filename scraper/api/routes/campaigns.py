"""API routes for campaign management (proxy to MailWizz)."""

from fastapi import APIRouter, Depends

from scraper.api.auth import verify_hmac
from scraper.database import get_db_session

router = APIRouter()


@router.get("/{campaign_id}/stats", dependencies=[Depends(verify_hmac)])
async def get_campaign_stats(campaign_id: str):
    """Get campaign statistics from sync logs."""
    with get_db_session() as session:
        total_sent = session.execute(
            """
            SELECT COUNT(*) FROM validated_contacts
            WHERE status = 'sent_to_mailwizz'
            """
        ).scalar()

        total_bounced = session.execute(
            """
            SELECT COUNT(*) FROM validated_contacts
            WHERE status = 'bounced'
            """
        ).scalar()

        by_platform = session.execute(
            """
            SELECT platform, status, COUNT(*) as count
            FROM validated_contacts
            WHERE status IN ('sent_to_mailwizz', 'bounced', 'failed')
            GROUP BY platform, status
            """
        ).mappings().all()

    return {
        "campaign_id": campaign_id,
        "total_sent": total_sent,
        "total_bounced": total_bounced,
        "by_platform": [dict(r) for r in by_platform],
    }
