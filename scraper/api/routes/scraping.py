"""API routes for scraping job management."""

import json

from fastapi import APIRouter, Depends

from scraper.api.auth import verify_hmac
from scraper.database import get_db_session

router = APIRouter()


@router.post("/jobs", dependencies=[Depends(verify_hmac)])
async def create_scraping_job(payload: dict):
    """Create a new scraping job."""
    with get_db_session() as session:
        result = session.execute(
            """
            INSERT INTO scraping_jobs
                (name, source_type, config, default_category,
                 default_platform, default_tags, auto_inject_mailwizz)
            VALUES
                (:name, :source_type, :config, :category,
                 :platform, :tags, :auto_inject)
            RETURNING id
            """,
            {
                "name": payload.get("name", "API Job"),
                "source_type": payload["source_type"],
                "config": json.dumps(payload.get("config", {})),
                "category": payload.get("category"),
                "platform": payload.get("platform"),
                "tags": json.dumps(payload.get("tags", [])),
                "auto_inject": payload.get("auto_inject_mailwizz", True),
            },
        )
        job_id = result.scalar()

    return {"job_id": job_id, "status": "created"}


@router.get("/jobs/{job_id}/status", dependencies=[Depends(verify_hmac)])
async def get_job_status(job_id: int):
    """Get status of a scraping job."""
    with get_db_session() as session:
        result = session.execute(
            """
            SELECT id, name, source_type, status, progress,
                   pages_scraped, contacts_extracted, errors_count,
                   created_at, started_at, completed_at
            FROM scraping_jobs
            WHERE id = :id
            """,
            {"id": job_id},
        ).mappings().first()

        if not result:
            return {"error": "Job not found"}

    return dict(result)


@router.get("/jobs", dependencies=[Depends(verify_hmac)])
async def list_jobs():
    """List all scraping jobs."""
    with get_db_session() as session:
        results = session.execute(
            """
            SELECT id, name, source_type, status, progress,
                   contacts_extracted, created_at
            FROM scraping_jobs
            ORDER BY created_at DESC
            LIMIT 50
            """
        ).mappings().all()

    return {"jobs": [dict(r) for r in results]}
