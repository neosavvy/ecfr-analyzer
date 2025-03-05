import uuid
from datetime import date
from sqlalchemy import Column, String, Integer, Float, Date, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class AgencyRegulationDocumentHistoricalMetrics(Base):
    """
    Historical metrics for agency regulation documents.
    Captures metrics at specific points in time (typically year-end) to track changes over time.
    """
    __tablename__ = "agency_regulation_document_historical_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Date of the metrics snapshot (typically December 31 of each year)
    metrics_date = Column(Date, nullable=False, index=True)
    
    # Document metrics
    word_count = Column(Integer, nullable=False)
    paragraph_count = Column(Integer, nullable=False)
    sentence_count = Column(Integer, nullable=True)
    section_count = Column(Integer, nullable=True)
    subpart_count = Column(Integer, nullable=True)
    
    # Complexity metrics
    language_complexity_score = Column(Float, nullable=True)
    readability_score = Column(Float, nullable=True)  # e.g., Flesch-Kincaid
    average_sentence_length = Column(Float, nullable=True)
    average_word_length = Column(Float, nullable=True)
    
    # Author metrics
    total_authors = Column(Integer, nullable=True)  # Number of unique authors who have touched the document
    revision_authors = Column(Integer, nullable=True)  # Number of authors who touched the document in this revision
    
    # Additional metrics from system design
    simplicity_score = Column(Float, nullable=True)  # Overall understandability score
    
    # Raw text content for reference (optional, could be large)
    content_snapshot = Column(Text, nullable=True)
    
    # Foreign keys
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("agency_documents.id"), nullable=False)
    
    # Relationships
    agency = relationship("Agency", back_populates="historical_metrics")
    document = relationship("AgencyDocument", back_populates="historical_metrics")
    
    # Ensure we don't have duplicate metrics for the same document on the same date
    __table_args__ = (
        UniqueConstraint('document_id', 'metrics_date', name='uix_document_date'),
    )
    
    def __repr__(self):
        return f"<DocumentHistoricalMetrics(id={self.id}, document_id={self.document_id}, date={self.metrics_date})>" 