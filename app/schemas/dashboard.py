from pydantic import BaseModel

from app.models.application import ApplicationStatus


class DashboardSummary(BaseModel):
    counts_by_status: dict[ApplicationStatus, int]
    total: int
