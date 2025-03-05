import uuid
from sqlalchemy import Column, String, Date, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base

class DocumentContent(Base):
    __tablename__ = "document_contents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    descriptor_id = Column(UUID(as_uuid=True), ForeignKey("agency_title_search_descriptors.id"), nullable=False)
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=False)
    
    # Date of the document version
    version_date = Column(Date, nullable=False)
    
    # Content
    raw_xml = Column(Text, nullable=False)
    processed_text = Column(Text, nullable=True)
    
    # Relationships
    descriptor = relationship("AgencyTitleSearchDescriptor", back_populates="contents")
    agency = relationship("Agency")
    
    def __repr__(self):
        return f"<DocumentContent(id='{self.id}', version_date='{self.version_date}')>"
    
    @classmethod
    def from_api_response(cls, xml_content, descriptor_id, agency_id, version_date):
        """Create a DocumentContent instance from API response data"""
        return cls(
            descriptor_id=descriptor_id,
            agency_id=agency_id,
            version_date=version_date,
            raw_xml=xml_content,
            processed_text=None  # Will be processed later
        ) 