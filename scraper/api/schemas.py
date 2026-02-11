"""Pydantic schemas for API request/response validation."""

from pydantic import BaseModel, Field


class CreateScrapingJobRequest(BaseModel):
    source_type: str = Field(..., description="Spider type: google_search, google_maps, custom_urls")
    name: str = Field(default="API Job", description="Job name")
    config: dict = Field(default_factory=dict, description="Spider-specific config (query, urls, etc.)")
    category: str | None = Field(default=None, description="Default category override")
    platform: str | None = Field(default=None, description="Default platform override")
    tags: list[str] = Field(default_factory=list, description="Custom tags")
    auto_inject_mailwizz: bool = Field(default=True, description="Auto-sync to MailWizz")


class BounceFeedbackRequest(BaseModel):
    email: str = Field(..., description="Bounced email address")
    bounce_type: str = Field(default="hard", description="Bounce type: hard or soft")


class DeliveryFeedbackRequest(BaseModel):
    domain: str = Field(..., description="Email domain that received deliveries")
    count: int = Field(default=1, ge=1, description="Number of emails successfully delivered")


class JobStatusResponse(BaseModel):
    id: int
    name: str
    source_type: str
    status: str
    progress: float
    pages_scraped: int
    contacts_extracted: int
    errors_count: int
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class ContactStatsResponse(BaseModel):
    total_scraped: int
    total_validated: int
    sent_to_mailwizz: int
    pending_sync: int
    bounced: int
    by_platform: list[dict]


class WhoisLookupRequest(BaseModel):
    domain: str = Field(..., description="Domain to lookup", min_length=3)


class HealthResponse(BaseModel):
    status: str
    service: str
    postgres: bool
    redis: bool
