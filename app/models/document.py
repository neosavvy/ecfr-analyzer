import uuid
from sqlalchemy import Column, String, Text, JSON, ForeignKey, DateTime, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional

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
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=True)  # Nullable for now during migration
    
    # Relationships
    agency = relationship("Agency", back_populates="documents")
    historical_metrics = relationship("AgencyRegulationDocumentHistoricalMetrics", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AgencyDocument(title={self.title}, document_id={self.document_id})>"
    
    @classmethod
    def extract_agency_id_from_metadata(cls, agency_metadata: dict) -> Optional[int]:
        """
        Extract agency ID from document metadata.
        Returns None if agency ID cannot be determined.
        """
        if not agency_metadata:
            return None
            
        # The agency ID should be stored in the metadata
        # You'll need to adjust this logic based on your actual metadata structure
        try:
            if isinstance(agency_metadata, dict):
                # Try to get agency_id directly if it exists
                if 'agency_id' in agency_metadata:
                    return int(agency_metadata['agency_id'])
                    
                # If no direct agency_id, try to get it from hierarchy if it exists
                if 'hierarchy' in agency_metadata:
                    hierarchy = agency_metadata['hierarchy']
                    if 'agency_id' in hierarchy:
                        return int(hierarchy['agency_id'])
                        
            return None
        except (ValueError, TypeError, KeyError):
            return None 