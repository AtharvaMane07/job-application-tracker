from datetime import datetime

from pydantic import BaseModel, Field

from app.models.interview_round import InterviewOutcome


class InterviewRoundCreate(BaseModel):
    round_type: str = Field(min_length=1, max_length=100)
    scheduled_date: datetime
    outcome: InterviewOutcome = InterviewOutcome.pending
    notes: str | None = None


class InterviewRoundUpdate(BaseModel):
    round_type: str | None = Field(default=None, min_length=1, max_length=100)
    scheduled_date: datetime | None = None
    outcome: InterviewOutcome | None = None
    notes: str | None = None


class InterviewRoundOut(BaseModel):
    id: int
    application_id: int
    round_type: str
    scheduled_date: datetime
    outcome: InterviewOutcome
    notes: str | None

    model_config = {"from_attributes": True}
