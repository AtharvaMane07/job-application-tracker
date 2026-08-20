from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.application import ApplicationStatus


class ApplicationCreate(BaseModel):
    company: str = Field(min_length=1, max_length=255)
    role: str = Field(min_length=1, max_length=255)
    status: ApplicationStatus = ApplicationStatus.applied
    applied_date: date
    notes: str | None = None


class ApplicationUpdate(BaseModel):
    """All fields optional — PATCH semantics, partial update."""

    company: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = Field(default=None, min_length=1, max_length=255)
    status: ApplicationStatus | None = None
    applied_date: date | None = None
    notes: str | None = None


class ApplicationOut(BaseModel):
    id: int
    company: str
    role: str
    status: ApplicationStatus
    applied_date: date
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
