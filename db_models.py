"""SQLAlchemy ORM model for analysis jobs."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func

from database import Base


class AnalysisJob(Base):
    """Represents one analysis request submitted by the user."""
    __tablename__ = "analysis_jobs"

    job_id = Column(String, primary_key=True, index=True)
    query = Column(String, nullable=False)
    filename = Column(String, nullable=False)

    # queued → running → done | failed
    status = Column(String, default="queued", nullable=False)

    # JSON blob of all four agents' structured outputs (set when status=done)
    result = Column(JSON, nullable=True)

    # Error message (set when status=failed)
    error = Column(String, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
