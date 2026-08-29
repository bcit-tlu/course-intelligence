"""SQLAlchemy models for job tracking and results storage."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all models."""


class JobStatus(str, enum.Enum):
    """Lifecycle states of a processing job."""

    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(Base):
    """A processing job: one uploaded course module."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        Text, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"),
        nullable=False,
        default=JobStatus.queued,
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    learning_objectives: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tenant_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_step: Mapped[str | None] = mapped_column(Text, nullable=True)
    step_progress: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    results: Mapped[list["Result"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Job {self.id} {self.status.value} {self.filename!r}>"


class Result(Base):
    """A single learning element produced from a job."""

    __tablename__ = "results"

    id: Mapped[str] = mapped_column(
        Text, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    job_id: Mapped[str] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    blooms_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    blooms_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_page: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    job: Mapped[Job] = relationship(back_populates="results")

    def __repr__(self) -> str:
        return f"<Result {self.id} job={self.job_id} {self.topic!r}>"
