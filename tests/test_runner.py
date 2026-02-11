"""Tests for the spider runner module."""

import subprocess
import threading

import pytest
from unittest.mock import patch, MagicMock, call


class TestRunSpider:
    """Tests for run_spider function."""

    @patch("scraper.runner._update_job_status")
    def test_unknown_source_type_marks_failed(self, mock_update):
        """An unknown source_type should immediately mark the job as failed."""
        from scraper.runner import run_spider

        run_spider(job_id=99, source_type="nonexistent_type", config={})
        mock_update.assert_called_once_with(99, "failed")

    @patch("scraper.runner.threading.Thread")
    @patch("scraper.runner._update_job_status")
    def test_valid_source_type_launches_subprocess(self, mock_update, mock_thread_cls):
        """A valid source_type should launch a background thread."""
        from scraper.runner import run_spider

        mock_thread_instance = MagicMock()
        mock_thread_cls.return_value = mock_thread_instance

        run_spider(
            job_id=1,
            source_type="google_search",
            config={"query": "avocat paris"},
        )

        # Thread should be created and started
        mock_thread_cls.assert_called_once()
        thread_kwargs = mock_thread_cls.call_args
        assert thread_kwargs.kwargs["daemon"] is True
        assert "spider-job-1" in thread_kwargs.kwargs["name"]
        mock_thread_instance.start.assert_called_once()

        # _update_job_status should NOT be called with "failed" (unknown type branch)
        mock_update.assert_not_called()

    @patch("scraper.runner.threading.Thread")
    @patch("scraper.runner._update_job_status")
    def test_resume_flag_launches_thread(self, mock_update, mock_thread_cls):
        """run_spider with resume=True should launch a thread just like a normal run."""
        from scraper.runner import run_spider

        mock_thread_instance = MagicMock()
        mock_thread_cls.return_value = mock_thread_instance

        run_spider(
            job_id=5,
            source_type="custom_urls",
            config={"urls": ["https://example.com"]},
            resume=True,
        )

        mock_thread_cls.assert_called_once()
        thread_kwargs = mock_thread_cls.call_args
        assert "spider-job-5" in thread_kwargs.kwargs["name"]
        mock_thread_instance.start.assert_called_once()


class TestUpdateJobStatus:
    """Tests for _update_job_status function."""

    def test_update_job_status_running(self):
        """Status 'running' should execute UPDATE with started_at = NOW()."""
        from scraper.runner import _update_job_status

        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.runner.get_db_session", return_value=mock_cm):
            _update_job_status(1, "running")

        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0])
        params = call_args[0][1]
        assert "started_at" in sql_text
        assert params["status"] == "running"
        assert params["id"] == 1

    def test_update_job_status_completed(self):
        """Status 'completed' should execute UPDATE with completed_at = NOW()."""
        from scraper.runner import _update_job_status

        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_session)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("scraper.runner.get_db_session", return_value=mock_cm):
            _update_job_status(1, "completed")

        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0])
        params = call_args[0][1]
        assert "completed_at" in sql_text
        assert params["status"] == "completed"
        assert params["id"] == 1
