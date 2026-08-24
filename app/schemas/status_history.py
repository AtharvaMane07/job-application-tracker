from datetime import datetime

from pydantic import BaseModel

from app.models.application import ApplicationStatus


class StatusHistoryOut(BaseModel):
    id: int
    application_id: int
    old_status: ApplicationStatus
    new_status: ApplicationStatus
    changed_at: datetime

    model_config = {"from_attributes": True}
