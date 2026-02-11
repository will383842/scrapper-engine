"""Pytest fixtures for scraper-pro tests."""

import os
import pytest

# Set test environment before any imports
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "test_scraper_db")
os.environ.setdefault("POSTGRES_USER", "test_user")
os.environ.setdefault("POSTGRES_PASSWORD", "test_pass")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("API_HMAC_SECRET", "test_secret_key")


@pytest.fixture
def sample_contact():
    """Sample scraped contact for testing."""
    return {
        "email": "john.doe@example.com",
        "name": "John Doe",
        "phone": "+33612345678",
        "website": "https://www.example-law.com",
        "address": "123 Rue de Paris, 75001 Paris",
        "social_media": {"linkedin": "https://linkedin.com/in/johndoe"},
        "source_type": "google_search",
        "source_url": "https://www.example-law.com/contact",
        "domain": "www.example-law.com",
        "country": "FR",
        "keywords": "avocat international paris",
        "job_id": 1,
    }


@pytest.fixture
def sample_contacts_batch():
    """Batch of sample contacts for testing."""
    return [
        {
            "email": f"contact{i}@domain{i}.com",
            "name": f"Contact {i}",
            "phone": f"+3361234567{i}",
            "website": f"https://domain{i}.com",
            "source_type": "google_search",
            "source_url": f"https://domain{i}.com/contact",
            "domain": f"domain{i}.com",
            "country": "FR",
            "keywords": "avocat paris",
            "job_id": 1,
        }
        for i in range(10)
    ]
