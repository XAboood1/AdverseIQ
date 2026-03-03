import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, JSON, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    strategy = Column(String, nullable=False)
    urgency = Column(String, nullable=False)
    input_data = Column(JSON, nullable=False)   # the original AnalysisRequest
    result_data = Column(JSON, nullable=False)  # the full AnalysisResult