import enum
from datetime import date, datetime

from sqlalchemy import String, Integer, Date, DateTime, Enum, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApplicationStatus(str, enum.Enum):
    applied = "applied"
    screening = "screening"
    interview = "interview"
    offer = "offer"
    rejected = "rejected"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # NOTE: no ForeignKey("users.id") yet — the users table doesn't exist
    # until Week 3 auth lands. Plain column now, FK constraint added via
    # an Alembic migration in Week 3, not by editing this file blindly.
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    company: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status"),
        nullable=False,
        default=ApplicationStatus.applied,
    )
    applied_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Application id={self.id} company={self.company!r} status={self.status}>"
