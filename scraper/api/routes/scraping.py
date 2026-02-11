"""API routes for scraping job management."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from scraper.api.auth import verify_hmac
from scraper.api.schemas import CreateScrapingJobRequest
from scraper.database import get_db_session
from scraper.runner import run_spider, SPIDER_MAP

router = APIRouter()


@router.post("/jobs", dependencies=[Depends(verify_hmac)])
async def create_scraping_job(payload: CreateScrapingJobRequest):
    """Create a new scraping job."""
    if payload.source_type not in SPIDER_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source_type '{payload.source_type}'. Must be one of: {list(SPIDER_MAP.keys())}"
        )

    with get_db_session() as session:
        result = session.execute(
            text("""
            INSERT INTO scraping_jobs
                (name, source_type, config, default_category,
                 default_platform, default_tags, auto_inject_mailwizz)
            VALUES
                (:name, :source_type, :config, :category,
                 :platform, :tags, :auto_inject)
            RETURNING id
            """),
            {
                "name": payload.name,
                "source_type": payload.source_type,
                "config": json.dumps(payload.config),
                "category": payload.category,
                "platform": payload.platform,
                "tags": json.dumps(payload.tags),
                "auto_inject": payload.auto_inject_mailwizz,
            },
        )
        job_id = result.scalar()

    run_spider(job_id, payload.source_type, payload.config)

    return {"job_id": job_id, "status": "created"}


@router.post("/jobs/{job_id}/resume", dependencies=[Depends(verify_hmac)])
async def resume_scraping_job(job_id: int):
    """Resume a failed or paused scraping job from its last checkpoint."""
    with get_db_session() as session:
        result = session.execute(
            text("""
            SELECT id, source_type, config, status, checkpoint_data, resume_count
            FROM scraping_jobs
            WHERE id = :id
            """),
            {"id": job_id},
        ).mappings().first()

        if not result:
            raise HTTPException(status_code=404, detail=f"Job #{job_id} not found")

        if result["status"] not in ("failed", "paused"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resume job with status '{result['status']}'. Only 'failed' or 'paused' jobs can be resumed."
            )

        checkpoint = result["checkpoint_data"]
        if not checkpoint or checkpoint == "{}":
            raise HTTPException(
                status_code=400,
                detail=f"Job #{job_id} has no checkpoint data to resume from."
            )

        # Update resume count and reset status
        session.execute(
            text("""
            UPDATE scraping_jobs
            SET status = 'pending',
                resume_count = resume_count + 1,
                completed_at = NULL,
                updated_at = NOW()
            WHERE id = :id
            """),
            {"id": job_id},
        )

    config = json.loads(result["config"]) if isinstance(result["config"], str) else result["config"]
    run_spider(job_id, result["source_type"], config, resume=True)

    return {
        "job_id": job_id,
        "status": "resuming",
        "resume_count": (result["resume_count"] or 0) + 1,
        "checkpoint": json.loads(checkpoint) if isinstance(checkpoint, str) else checkpoint,
    }


@router.get("/jobs/{job_id}/status", dependencies=[Depends(verify_hmac)])
async def get_job_status(job_id: int):
    """Get status of a scraping job."""
    with get_db_session() as session:
        result = session.execute(
            text("""
            SELECT id, name, source_type, status, progress,
                   pages_scraped, contacts_extracted, errors_count,
                   created_at, started_at, completed_at,
                   checkpoint_data, resume_count
            FROM scraping_jobs
            WHERE id = :id
            """),
            {"id": job_id},
        ).mappings().first()

        if not result:
            raise HTTPException(status_code=404, detail=f"Job #{job_id} not found")

    return dict(result)


@router.post("/jobs/{job_id}/pause", dependencies=[Depends(verify_hmac)])
async def pause_scraping_job(job_id: int):
    """Pause a running scraping job."""
    with get_db_session() as session:
        result = session.execute(
            text("SELECT id, status FROM scraping_jobs WHERE id = :id"),
            {"id": job_id},
        ).mappings().first()

        if not result:
            raise HTTPException(status_code=404, detail=f"Job #{job_id} not found")

        if result["status"] != "running":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot pause job with status '{result['status']}'. Only 'running' jobs can be paused."
            )

        session.execute(
            text("""
            UPDATE scraping_jobs
            SET status = 'paused', updated_at = NOW()
            WHERE id = :id
            """),
            {"id": job_id},
        )

    return {"job_id": job_id, "status": "paused"}


@router.post("/jobs/{job_id}/cancel", dependencies=[Depends(verify_hmac)])
async def cancel_scraping_job(job_id: int):
    """Cancel a running or paused scraping job."""
    with get_db_session() as session:
        result = session.execute(
            text("SELECT id, status FROM scraping_jobs WHERE id = :id"),
            {"id": job_id},
        ).mappings().first()

        if not result:
            raise HTTPException(status_code=404, detail=f"Job #{job_id} not found")

        if result["status"] not in ("running", "paused", "pending"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel job with status '{result['status']}'."
            )

        session.execute(
            text("""
            UPDATE scraping_jobs
            SET status = 'cancelled', completed_at = NOW(), updated_at = NOW()
            WHERE id = :id
            """),
            {"id": job_id},
        )

    return {"job_id": job_id, "status": "cancelled"}


@router.get("/jobs", dependencies=[Depends(verify_hmac)])
async def list_jobs():
    """List all scraping jobs."""
    with get_db_session() as session:
        results = session.execute(
            text("""
            SELECT id, name, source_type, status, progress,
                   contacts_extracted, created_at
            FROM scraping_jobs
            ORDER BY created_at DESC
            LIMIT 50
            """)
        ).mappings().all()

    return {"jobs": [dict(r) for r in results]}
