from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Boolean,
    Text,
    Enum as SAEnum,
)
from sqlalchemy.sql import func
import enum

from src.core.database import Base


# --- Enums for Status and Severity ---
class JobStatusEnum(str, enum.Enum):
    NEW = "NEW"
    EXEC = "EXEC"
    ABEND = "ABEND"
    ERROR = "ERROR"
    FAIL = "FAIL"
    SUCCESS = "SUCCESS"
    UNKNOWN = "UNKNOWN"
    # Add other HWA/TWS statuses as needed


class AlertSeverityEnum(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# --- SQLAlchemy Models ---


class JobStatusHistory(Base):
    """
    Represents the historical log of job status changes.
    """

    __tablename__ = "job_status_history"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, index=True, nullable=False)
    job_name = Column(String, index=True, nullable=False)
    old_status = Column(String)
    new_status = Column(String, nullable=False)
    workstation = Column(String, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    duration = Column(Float, nullable=True)  # Duration in seconds
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<JobStatusHistory(job_name='{self.job_name}', status='{self.new_status}', time='{self.timestamp}')>"


class AlertRule(Base):
    """
    Defines a rule for triggering an alert based on job status.
    """

    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    job_name_pattern = Column(
        String, nullable=False, default="*"
    )  # Glob pattern, e.g., "PAYROLL_*"
    status_trigger = Column(SAEnum(JobStatusEnum), nullable=False)
    severity = Column(
        SAEnum(AlertSeverityEnum), nullable=False, default=AlertSeverityEnum.HIGH
    )
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<AlertRule(name='{self.name}', pattern='{self.job_name_pattern}', status='{self.status_trigger}')>"


# --- Database Setup (optional, can be in core.database) ---
# This part can be expanded and moved to a central database management file

# Example of how to create the engine and session
# DATABASE_URL = config.DATABASE_URL # Assuming this will be in the config
# engine = create_engine(DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# def create_db_and_tables():
#     Base.metadata.create_all(bind=engine)
