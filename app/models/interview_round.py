import enum
from datetime import datetime

from sqlalchemy import Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InterviewOutcome(str, enum.Enum):
    pending = "pending"
    passed = "passed"
    failed = "failed"
    cancelled = "cancelled"


class InterviewRound(Base):
    __tablename__ = "interview_rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )

    round_type: Mapped[str] = mapped_column(String(100), nullable=False)
    scheduled_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    outcome: Mapped[InterviewOutcome] = mapped_column(
        Enum(InterviewOutcome, name="interview_outcome"),
        nullable=False,
        default=InterviewOutcome.pending,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<InterviewRound id={self.id} application_id={self.application_id} type={self.round_type!r}>"
