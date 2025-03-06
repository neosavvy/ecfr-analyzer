import uuid
from sqlalchemy import Column, String, Date, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import Base

class AgencyDocumentCount(Base):
    __tablename__ = "agency_document_counts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=False)
    
    # Query information
    query_date = Column(Date, nullable=False, default=datetime.now().date)
    reference_date = Column(Date, nullable=False)  # The date used in the API call
    target_year = Column(Integer, nullable=True)  # The target year used for filtering documents
    
    # Count and pagination
    total_count = Column(Integer, nullable=False)
    current_page = Column(Integer, nullable=False, default=0)
    per_page = Column(Integer, nullable=False, default=20)
    
    # Status
    is_complete = Column(Integer, nullable=False, default=0)  # 0=not started, 1=in progress, 2=complete
    
    # Relationship with agency
    agency = relationship("Agency")
    
    def __repr__(self):
        return f"<AgencyDocumentCount(agency_id='{self.agency_id}', total_count='{self.total_count}', current_page='{self.current_page}')>"
    
    @classmethod
    def from_api_response(cls, agency_id, count_data, reference_date=None, target_year=None):
        """Create an AgencyDocumentCount instance from API response data"""
        if reference_date is None:
            reference_date = datetime.now().date()
            
        return cls(
            agency_id=agency_id,
            reference_date=reference_date,
            total_count=count_data.get("meta", {}).get("total_count", 0),
            current_page=0,
            is_complete=0,
            target_year=target_year
        ) 