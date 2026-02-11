"""Tests for the FastAPI endpoints."""

import hashlib
import hmac
import json
import time
import os

import pytest
from unittest.mock import patch, MagicMock, PropertyMock

os.environ["API_HMAC_SECRET"] = "test_secret"

from fastapi.testclient import TestClient
from scraper.api.main import app

client = TestClient(app)


def _make_auth_headers(body: str = "") -> dict:
    """Generate valid HMAC auth headers for testing."""
    secret = "test_secret"
    timestamp = str(int(time.time()))
    message = f"{timestamp}.{body}"
    signature = hmac.new(
        secret.encode(), message.encode(), hashlib.sha256
    ).hexdigest()
    return {
        "X-Signature": signature,
        "X-Timestamp": timestamp,
    }


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_check(self):
        with patch("scraper.api.main._check_postgres", return_value=True):
            with patch("scraper.api.main._check_redis", return_value=True):
                response = client.get("/health")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "ok"
                assert data["service"] == "scraper-pro"
                assert data["postgres"] is True
                assert data["redis"] is True

    def test_health_degraded(self):
        """When Postgres is down but Redis is up, status should be degraded."""
        with patch("scraper.api.main._check_postgres", return_value=False):
            with patch("scraper.api.main._check_redis", return_value=True):
                response = client.get("/health")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "degraded"
                assert data["postgres"] is False
                assert data["redis"] is True

    def test_health_all_down(self):
        """When both Postgres and Redis are down, status should be degraded."""
        with patch("scraper.api.main._check_postgres", return_value=False):
            with patch("scraper.api.main._check_redis", return_value=False):
                response = client.get("/health")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "degraded"
                assert data["postgres"] is False
                assert data["redis"] is False


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestAuth:
    def test_missing_signature(self):
        response = client.get("/api/v1/contacts/stats")
        assert response.status_code == 401

    def test_invalid_signature(self):
        response = client.get(
            "/api/v1/contacts/stats",
            headers={"X-Signature": "invalid", "X-Timestamp": str(int(time.time()))},
        )
        assert response.status_code == 401

    def test_valid_auth_header(self):
        """A request with a valid HMAC signature should pass auth and reach the handler."""
        headers = _make_auth_headers()
        mock_session = MagicMock()
        mock_session.execute.return_value = MagicMock(
            scalar=MagicMock(return_value=42),
            mappings=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))),
        )
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.api.routes.contacts.get_db_session", return_value=mock_cm):
            response = client.get("/api/v1/contacts/stats", headers=headers)
            # Should not be 401/403 -- auth passed
            assert response.status_code == 200

    def test_expired_timestamp(self):
        """A request with a timestamp older than 5 minutes should be rejected."""
        secret = "test_secret"
        old_timestamp = str(int(time.time()) - 600)  # 10 minutes ago
        body_str = ""
        message = f"{old_timestamp}.{body_str}"
        signature = hmac.new(
            secret.encode(), message.encode(), hashlib.sha256
        ).hexdigest()
        headers = {
            "X-Signature": signature,
            "X-Timestamp": old_timestamp,
        }
        response = client.get("/api/v1/contacts/stats", headers=headers)
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Contacts - Bounce feedback
# ---------------------------------------------------------------------------

class TestBounceFeedback:
    def test_bounce_feedback_valid(self):
        """Valid bounce feedback should update the DB and return ok."""
        body = json.dumps({"email": "bounced@example.com", "bounce_type": "hard"})
        headers = _make_auth_headers(body)
        headers["Content-Type"] = "application/json"

        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.api.routes.contacts.get_db_session", return_value=mock_cm):
            response = client.post(
                "/api/v1/contacts/bounce-feedback",
                content=body,
                headers=headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["email"] == "bounced@example.com"
            assert data["bounce_type"] == "hard"
            # Verify two SQL executions happened (UPDATE + INSERT)
            assert mock_session.execute.call_count == 2

    def test_bounce_feedback_invalid_email(self):
        """An email without @ should be rejected with 400."""
        body = json.dumps({"email": "not-an-email", "bounce_type": "hard"})
        headers = _make_auth_headers(body)
        headers["Content-Type"] = "application/json"

        with patch("scraper.api.routes.contacts.get_db_session"):
            response = client.post(
                "/api/v1/contacts/bounce-feedback",
                content=body,
                headers=headers,
            )
            assert response.status_code == 400
            assert "email" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Scraping jobs
# ---------------------------------------------------------------------------

class TestScrapingJobs:
    def test_create_job_valid(self):
        """A valid job creation should insert into DB and launch the spider."""
        body = json.dumps({
            "source_type": "google_search",
            "name": "Test Job",
            "config": {"query": "avocat paris"},
        })
        headers = _make_auth_headers(body)
        headers["Content-Type"] = "application/json"

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        mock_session.execute.return_value = mock_result

        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.api.routes.scraping.get_db_session", return_value=mock_cm):
            with patch("scraper.api.routes.scraping.run_spider") as mock_run:
                response = client.post(
                    "/api/v1/scraping/jobs",
                    content=body,
                    headers=headers,
                )
                assert response.status_code == 200
                data = response.json()
                assert data["job_id"] == 42
                assert data["status"] == "created"
                mock_run.assert_called_once_with(
                    42, "google_search", {"query": "avocat paris"}
                )

    def test_create_job_invalid_source_type(self):
        """An invalid source_type should be rejected with 400."""
        body = json.dumps({
            "source_type": "nonexistent_spider",
            "name": "Bad Job",
            "config": {},
        })
        headers = _make_auth_headers(body)
        headers["Content-Type"] = "application/json"

        response = client.post(
            "/api/v1/scraping/jobs",
            content=body,
            headers=headers,
        )
        assert response.status_code == 400
        assert "nonexistent_spider" in response.json()["detail"]

    def test_get_job_not_found(self):
        """Requesting a non-existent job should return 404."""
        headers = _make_auth_headers()

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.api.routes.scraping.get_db_session", return_value=mock_cm):
            response = client.get(
                "/api/v1/scraping/jobs/99999/status",
                headers=headers,
            )
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_resume_job_success(self):
        """Resuming a failed job with checkpoint data should succeed."""
        headers = _make_auth_headers()

        mock_session = MagicMock()
        # First call: SELECT to get job info
        mock_job = {
            "id": 10,
            "source_type": "google_search",
            "config": json.dumps({"query": "avocat paris"}),
            "status": "failed",
            "checkpoint_data": json.dumps({"last_page": 20, "contacts_found": 5}),
            "resume_count": 0,
        }
        mock_result_select = MagicMock()
        mock_result_select.mappings.return_value.first.return_value = mock_job
        # Second call: UPDATE resume_count
        mock_result_update = MagicMock()

        mock_session.execute.side_effect = [mock_result_select, mock_result_update]

        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.api.routes.scraping.get_db_session", return_value=mock_cm):
            with patch("scraper.api.routes.scraping.run_spider") as mock_run:
                response = client.post(
                    "/api/v1/scraping/jobs/10/resume",
                    headers=headers,
                )
                assert response.status_code == 200
                data = response.json()
                assert data["job_id"] == 10
                assert data["status"] == "resuming"
                assert data["resume_count"] == 1
                mock_run.assert_called_once_with(
                    10, "google_search", {"query": "avocat paris"}, resume=True
                )

    def test_resume_job_wrong_status(self):
        """Resuming a running/completed job should fail with 400."""
        headers = _make_auth_headers()

        mock_session = MagicMock()
        mock_job = {
            "id": 10,
            "source_type": "google_search",
            "config": "{}",
            "status": "running",
            "checkpoint_data": "{}",
            "resume_count": 0,
        }
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = mock_job
        mock_session.execute.return_value = mock_result

        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.api.routes.scraping.get_db_session", return_value=mock_cm):
            response = client.post(
                "/api/v1/scraping/jobs/10/resume",
                headers=headers,
            )
            assert response.status_code == 400
            assert "cannot resume" in response.json()["detail"].lower()

    def test_resume_job_no_checkpoint(self):
        """Resuming a failed job without checkpoint data should fail."""
        headers = _make_auth_headers()

        mock_session = MagicMock()
        mock_job = {
            "id": 10,
            "source_type": "google_search",
            "config": "{}",
            "status": "failed",
            "checkpoint_data": "{}",
            "resume_count": 0,
        }
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = mock_job
        mock_session.execute.return_value = mock_result

        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.api.routes.scraping.get_db_session", return_value=mock_cm):
            response = client.post(
                "/api/v1/scraping/jobs/10/resume",
                headers=headers,
            )
            assert response.status_code == 400
            assert "no checkpoint" in response.json()["detail"].lower()

    def test_resume_job_not_found(self):
        """Resuming a non-existent job should return 404."""
        headers = _make_auth_headers()

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.api.routes.scraping.get_db_session", return_value=mock_cm):
            response = client.post(
                "/api/v1/scraping/jobs/99999/resume",
                headers=headers,
            )
            assert response.status_code == 404
