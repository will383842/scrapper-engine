"""API routes for campaign/sending statistics."""

from fastapi import APIRouter, Depends
from sqlalchemy import text

from scraper.api.auth import verify_hmac
from scraper.database import get_db_session

router = APIRouter()


@router.get("/stats", dependencies=[Depends(verify_hmac)])
async def get_global_campaign_stats():
    """Get global sending statistics across all campaigns."""
    with get_db_session() as session:
        total_sent = session.execute(
            text("""
            SELECT COUNT(*) FROM validated_contacts
            WHERE status = 'sent_to_mailwizz'
            """)
        ).scalar()

        total_bounced = session.execute(
            text("""
            SELECT COUNT(*) FROM validated_contacts
            WHERE status = 'bounced'
            """)
        ).scalar()

        by_platform = session.execute(
            text("""
            SELECT platform, status, COUNT(*) as count
            FROM validated_contacts
            WHERE status IN ('sent_to_mailwizz', 'bounced', 'failed')
            GROUP BY platform, status
            """)
        ).mappings().all()

    return {
        "total_sent": total_sent,
        "total_bounced": total_bounced,
        "by_platform": [dict(r) for r in by_platform],
    }
