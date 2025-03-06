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
    
    # Detailed readability metrics
    combined_readability_score = Column(Float, nullable=True, comment="Combined weighted score from all readability metrics (0-100)")
    flesch_reading_ease = Column(Float, nullable=True, comment="Flesch Reading Ease score (0-100)")
    smog_index_score = Column(Float, nullable=True, comment="SMOG Index score normalized to 0-100")
    automated_readability_score = Column(Float, nullable=True, comment="Automated Readability Index normalized to 0-100")
    
    # Author metrics
    total_authors = Column(Integer, nullable=True)  # Number of unique authors who have touched the document
    revision_authors = Column(Integer, nullable=True)  # Number of authors who touched the document in this revision
    
    # Additional metrics from system design
    simplicity_score = Column(Float, nullable=True)  # Overall understandability score
    
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
        return f"<AgencyRegulationDocumentHistoricalMetrics(id='{self.id}', metrics_date='{self.metrics_date}')>" 