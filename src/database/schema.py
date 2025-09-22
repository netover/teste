import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    JSON,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class JobStatusHistory(Base):
    """
    SQLAlchemy model for storing the historical status of jobs.
    """

    __tablename__ = "job_status_history"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, index=True, nullable=False)
    job_stream_name = Column(String, index=True)
    workstation_name = Column(String, index=True)
    status = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    details = Column(JSON, nullable=True)

    def __repr__(self):
        return (
            f"<JobStatusHistory(id={self.id}, job_id='{self.job_id}', "
            f"job_stream_name='{self.job_stream_name}', status='{self.status}')>"
        )
