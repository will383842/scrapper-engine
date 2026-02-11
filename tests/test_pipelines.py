"""Tests for Scrapy pipelines: deduplication, validation, and Postgres storage."""

import json

import pytest
import redis
from unittest.mock import patch, MagicMock

from scrapy.exceptions import DropItem


# ---------------------------------------------------------------------------
# DeduplicationPipeline
# ---------------------------------------------------------------------------

class TestDeduplicationPipeline:
    """Tests for DeduplicationPipeline."""

    def _make_pipeline(self, redis_client=None):
        """Create a DeduplicationPipeline with optional mocked Redis."""
        from scraper.utils.pipelines import DeduplicationPipeline

        pipeline = DeduplicationPipeline()
        if redis_client is not None:
            pipeline.redis_client = redis_client
        else:
            # In-memory fallback mode
            pipeline.redis_client = None
            pipeline._memory_set = set()
        return pipeline

    def _make_spider(self, job_id="test_job"):
        spider = MagicMock()
        spider.job_id = job_id
        return spider

    def test_drops_empty_email(self):
        """Items with no email should be dropped."""
        pipeline = self._make_pipeline()
        spider = self._make_spider()

        with pytest.raises(DropItem, match="No email"):
            pipeline.process_item({"email": ""}, spider)

        with pytest.raises(DropItem, match="No email"):
            pipeline.process_item({}, spider)

    def test_drops_duplicate_email(self):
        """Redis reports the email already seen -> item should be dropped."""
        mock_redis = MagicMock()
        mock_redis.sismember.return_value = True

        pipeline = self._make_pipeline(redis_client=mock_redis)
        spider = self._make_spider()

        with pytest.raises(DropItem, match="Duplicate email"):
            pipeline.process_item({"email": "dupe@example.com"}, spider)

    def test_passes_new_email(self):
        """Redis says the email is new -> item should pass through."""
        mock_redis = MagicMock()
        mock_redis.sismember.return_value = False

        pipeline = self._make_pipeline(redis_client=mock_redis)
        spider = self._make_spider()

        result = pipeline.process_item({"email": "new@example.com"}, spider)
        assert result["email"] == "new@example.com"
        mock_redis.sadd.assert_called_once()
        mock_redis.expire.assert_called_once()

    def test_redis_down_fallback(self):
        """When Redis raises ConnectionError, pipeline should fall back to in-memory set."""
        mock_redis = MagicMock()
        mock_redis.sismember.side_effect = redis.ConnectionError("Redis gone")

        pipeline = self._make_pipeline(redis_client=mock_redis)
        spider = self._make_spider()

        # First call triggers fallback; since the in-memory set is fresh, item passes
        result = pipeline.process_item({"email": "fallback@example.com"}, spider)
        assert result["email"] == "fallback@example.com"
        # After fallback, redis_client should be None
        assert pipeline.redis_client is None


# ---------------------------------------------------------------------------
# ValidationPipeline
# ---------------------------------------------------------------------------

class TestValidationPipeline:
    """Tests for ValidationPipeline."""

    def _make_pipeline(self):
        from scraper.utils.pipelines import ValidationPipeline
        return ValidationPipeline()

    def _make_spider(self):
        return MagicMock()

    def test_drops_invalid_email(self):
        """Email without @ sign should be dropped."""
        pipeline = self._make_pipeline()
        spider = self._make_spider()

        with pytest.raises(DropItem, match="Invalid email"):
            pipeline.process_item({"email": "no-at-sign"}, spider)

    def test_normalizes_email(self):
        """Uppercase emails should be lowercased."""
        pipeline = self._make_pipeline()
        spider = self._make_spider()

        result = pipeline.process_item({"email": "John.Doe@Example.COM"}, spider)
        assert result["email"] == "john.doe@example.com"

    def test_truncates_long_name(self):
        """Names longer than 255 characters should be truncated."""
        pipeline = self._make_pipeline()
        spider = self._make_spider()

        long_name = "A" * 500
        result = pipeline.process_item(
            {"email": "user@example.com", "name": long_name}, spider
        )
        assert len(result["name"]) == 255

    def test_passes_valid_item(self):
        """A well-formed item should pass through unchanged (except normalization)."""
        pipeline = self._make_pipeline()
        spider = self._make_spider()

        item = {
            "email": "valid@domain.com",
            "name": "  Jane Doe  ",
        }
        result = pipeline.process_item(item, spider)
        assert result["email"] == "valid@domain.com"
        assert result["name"] == "Jane Doe"


# ---------------------------------------------------------------------------
# PostgresPipeline
# ---------------------------------------------------------------------------

class TestPostgresPipeline:
    """Tests for PostgresPipeline."""

    def test_stores_contact(self):
        """Verify the pipeline calls SQL with correct parameters."""
        from scraper.utils.pipelines import PostgresPipeline

        pipeline = PostgresPipeline()
        spider = MagicMock()

        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        item = {
            "email": "store@example.com",
            "name": "Store Test",
            "phone": "+33600000000",
            "website": "https://example.com",
            "address": "123 Rue de Test",
            "social_media": {"linkedin": "https://linkedin.com/in/test"},
            "source_type": "google_search",
            "source_url": "https://example.com/contact",
            "domain": "example.com",
            "country": "FR",
            "keywords": "test keyword",
            "job_id": 7,
        }

        with patch("scraper.utils.pipelines.get_db_session", return_value=mock_cm):
            result = pipeline.process_item(item, spider)

        # Item should be returned unmodified
        assert result["email"] == "store@example.com"

        # Verify SQL was executed
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args
        sql_params = call_args[0][1]
        assert sql_params["email"] == "store@example.com"
        assert sql_params["name"] == "Store Test"
        assert sql_params["job_id"] == 7
        assert sql_params["source_type"] == "google_search"
        assert json.loads(sql_params["social_media"]) == {
            "linkedin": "https://linkedin.com/in/test"
        }


# ---------------------------------------------------------------------------
# ProgressTrackingPipeline
# ---------------------------------------------------------------------------

class TestProgressTrackingPipeline:
    """Tests for ProgressTrackingPipeline."""

    def _make_pipeline(self):
        from scraper.utils.pipelines import ProgressTrackingPipeline
        return ProgressTrackingPipeline()

    def test_passes_item_through(self):
        """Items should pass through the pipeline unchanged."""
        pipeline = self._make_pipeline()
        spider = MagicMock()
        item = {"email": "test@example.com", "job_id": 1}

        result = pipeline.process_item(item, spider)
        assert result["email"] == "test@example.com"

    def test_counts_per_job(self):
        """Pipeline should track counts per job_id."""
        pipeline = self._make_pipeline()
        spider = MagicMock()

        for i in range(5):
            pipeline.process_item({"email": f"test{i}@example.com", "job_id": 1}, spider)

        assert pipeline._counts[1] == 5

    def test_flushes_at_10_items(self):
        """Pipeline should flush to DB every 10 items."""
        pipeline = self._make_pipeline()
        spider = MagicMock()

        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.utils.pipelines.get_db_session", return_value=mock_cm):
            for i in range(10):
                pipeline.process_item({"email": f"test{i}@x.com", "job_id": 42}, spider)

        # Should have flushed once at count=10
        mock_session.execute.assert_called_once()

    def test_no_job_id_skips_tracking(self):
        """Items without job_id should not be tracked."""
        pipeline = self._make_pipeline()
        spider = MagicMock()

        result = pipeline.process_item({"email": "test@x.com"}, spider)
        assert result["email"] == "test@x.com"
        assert len(pipeline._counts) == 0

    def test_close_spider_flushes_remaining(self):
        """close_spider should flush any remaining counts."""
        pipeline = self._make_pipeline()
        spider = MagicMock()

        # Add 3 items (not a multiple of 10, so no auto-flush)
        for i in range(3):
            pipeline.process_item({"email": f"test{i}@x.com", "job_id": 7}, spider)

        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.utils.pipelines.get_db_session", return_value=mock_cm):
            pipeline.close_spider(spider)

        mock_session.execute.assert_called_once()
