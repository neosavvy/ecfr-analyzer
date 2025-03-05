import uuid
from sqlalchemy import Column, String, Date, Float, Boolean, JSON, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base

class AgencyTitleSearchDescriptor(Base):
    __tablename__ = "agency_title_search_descriptors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=False)
    
    # Date range
    starts_on = Column(Date, nullable=True)
    ends_on = Column(Date, nullable=True)
    
    # Type and structure
    type = Column(String, nullable=True)
    structure_index = Column(Integer, nullable=True)
    reserved = Column(Boolean, default=False)
    removed = Column(Boolean, default=False)
    
    # Hierarchies
    hierarchy = Column(JSON, default=dict)
    hierarchy_headings = Column(JSON, default=dict)
    headings = Column(JSON, default=dict)
    
    # Search-related fields
    full_text_excerpt = Column(String, nullable=True)
    score = Column(Float, nullable=True)
    change_types = Column(JSON, default=list)
    
    # Processing status
    processing_status = Column(Integer, default=0)  # 0=not processed, 1=processing, 2=completed, 3=error
    
    # Relationships
    agency = relationship("Agency", back_populates="search_descriptors")
    contents = relationship("DocumentContent", back_populates="descriptor", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AgencyTitleSearchDescriptor(id='{self.id}', type='{self.type}')>"
    
    @classmethod
    def from_api_response(cls, data, agency_id):
        """Create an AgencyTitleSearchDescriptor instance from API response data"""
        # Convert date strings to date objects if they exist
        starts_on = data.get("starts_on")
        ends_on = data.get("ends_on")
        
        # Keep dates as strings in the model - we'll handle conversion when needed
        return cls(
            agency_id=agency_id,
            starts_on=starts_on,
            ends_on=ends_on,
            type=data.get("type"),
            structure_index=data.get("structure_index"),
            reserved=data.get("reserved", False),
            removed=data.get("removed", False),
            hierarchy=data.get("hierarchy", {}),
            hierarchy_headings=data.get("hierarchy_headings", {}),
            headings=data.get("headings", {}),
            full_text_excerpt=data.get("full_text_excerpt"),
            score=data.get("score"),
            change_types=data.get("change_types", [])
        ) 