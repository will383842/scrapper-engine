"""API routes for scraping job management."""

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text

from scraper.api.auth import verify_hmac
from scraper.api.schemas import CreateScrapingJobRequest
from scraper.database import get_db_session
from scraper.runner import run_spider, SPIDER_MAP

router = APIRouter()


@router.post("/jobs/simple")
async def create_job_simple(
    request: Request,
    source_type: str,
    name: str,
    config: dict,
    max_results: int = 100,
):
    """
    Endpoint simplifié SANS authentification HMAC.

    ⚠️ DEV MODE ONLY - Accessible uniquement depuis localhost

    Usage:
        curl -X POST http://localhost:8000/api/v1/scraping/jobs/simple \\
          -H "Content-Type: application/json" \\
          -d '{
            "source_type": "custom_urls",
            "name": "Test Job",
            "config": {"urls": ["https://example.com"]},
            "max_results": 100
          }'

    Exemples de configurations:

    1. Custom URLs:
       {
         "source_type": "custom_urls",
         "config": {"urls": ["https://example.com", "https://example2.com"]}
       }

    2. Google Search:
       {
         "source_type": "google_search",
         "config": {"query": "avocat Paris", "max_results": 100, "country": "fr"}
       }

    3. Google Maps:
       {
         "source_type": "google_maps",
         "config": {"query": "avocat", "location": "Paris, France", "max_results": 50}
       }

    4. Blog Content:
       {
         "source_type": "blog_content",
         "config": {"start_url": "https://example.com/blog", "max_articles": 100}
       }
    """
    # Sécurité: localhost seulement
    client_host = request.client.host
    if client_host not in ["127.0.0.1", "localhost", "::1"]:
        raise HTTPException(
            status_code=403,
            detail="Dev mode: accessible uniquement depuis localhost"
        )

    # Valider source_type
    if source_type not in SPIDER_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source_type '{source_type}'. Must be one of: {list(SPIDER_MAP.keys())}"
        )

    # Ajouter max_results au config si applicable
    if source_type in ["google_search", "google_maps"] and "max_results" not in config:
        config["max_results"] = max_results
    elif source_type == "blog_content" and "max_articles" not in config:
        config["max_articles"] = max_results

    # Créer job sans HMAC
    with get_db_session() as session:
        result = session.execute(
            text("""
            INSERT INTO scraping_jobs
                (name, source_type, config, auto_inject_mailwizz)
            VALUES
                (:name, :source_type, :config, :auto_inject)
            RETURNING id
            """),
            {
                "name": name,
                "source_type": source_type,
                "config": json.dumps(config),
                "auto_inject": True,
            },
        )
        job_id = result.scalar()

    run_spider(job_id, source_type, config)

    return {
        "success": True,
        "job_id": job_id,
        "status": "created",
        "message": "Job créé avec succès (dev mode)",
    }


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


@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: int):
    """
    Get status of a scraping job.

    ⚠️ DEV MODE - Accessible sans authentification HMAC

    Usage:
        curl http://localhost:8000/api/v1/scraping/jobs/123/status
    """
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


@router.get("/jobs/{job_id}/logs")
async def get_job_logs(
    job_id: int,
    limit: int = 100,
    error_type: str | None = None,
):
    """
    Récupère les logs détaillés d'un job.

    ⚠️ DEV MODE - Accessible sans authentification HMAC

    Args:
        job_id: ID du job
        limit: Nombre max de logs (défaut: 100)
        error_type: Filtrer par type d'erreur (optionnel)

    Returns:
        {
            "job_id": 123,
            "logs": [
                {
                    "id": 1,
                    "timestamp": "2026-02-13T14:30:00Z",
                    "error_type": "ConnectionError",
                    "error_message": "Failed to connect to example.com",
                    "url": "https://example.com",
                    "proxy_used": "http://proxy.example.com:8080",
                    "stack_trace": "..."
                }
            ],
            "count": 45,
            "has_errors": true
        }

    Usage:
        # Tous les logs
        curl http://localhost:8000/api/v1/scraping/jobs/123/logs

        # Filtrer par type
        curl http://localhost:8000/api/v1/scraping/jobs/123/logs?error_type=TimeoutError

        # Limiter les résultats
        curl http://localhost:8000/api/v1/scraping/jobs/123/logs?limit=50
    """
    # Vérifier que le job existe
    with get_db_session() as session:
        job_check = session.execute(
            text("SELECT id, name, status FROM scraping_jobs WHERE id = :id"),
            {"id": job_id},
        ).mappings().first()

        if not job_check:
            raise HTTPException(status_code=404, detail=f"Job #{job_id} not found")

        # Construire la requête avec filtres optionnels
        query = """
            SELECT id, job_id, error_type, error_message, url, proxy_used, stack_trace, created_at
            FROM error_logs
            WHERE job_id = :job_id
        """
        params = {"job_id": job_id, "limit": limit}

        if error_type:
            query += " AND error_type = :error_type"
            params["error_type"] = error_type

        query += " ORDER BY created_at DESC LIMIT :limit"

        logs = session.execute(text(query), params).mappings().all()

    return {
        "job_id": job_id,
        "job_name": job_check["name"],
        "job_status": job_check["status"],
        "logs": [
            {
                "id": log["id"],
                "timestamp": log["created_at"].isoformat() if log["created_at"] else None,
                "error_type": log["error_type"],
                "error_message": log["error_message"],
                "url": log["url"],
                "proxy_used": log["proxy_used"],
                "stack_trace": log["stack_trace"],
            }
            for log in logs
        ],
        "count": len(logs),
        "has_errors": len(logs) > 0,
    }


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
