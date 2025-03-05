import uuid
from sqlalchemy import Column, String, Text, JSON, ForeignKey, DateTime, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import Base


class AgencyDocument(Base):
    __tablename__ = "agency_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    document_id = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=True)
    agency_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    # Foreign keys
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=False)
    
    # Relationships
    agency = relationship("Agency", back_populates="documents")
    historical_metrics = relationship("AgencyRegulationDocumentHistoricalMetrics", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AgencyDocument(title={self.title}, document_id={self.document_id})>" 