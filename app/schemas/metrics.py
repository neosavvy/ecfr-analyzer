from datetime import date, datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
import uuid


class HistoricalMetricsBase(BaseModel):
    """Base schema for historical metrics"""
    metrics_date: date
    word_count: int
    paragraph_count: int
    sentence_count: Optional[int] = None
    section_count: Optional[int] = None
    subpart_count: Optional[int] = None
    language_complexity_score: Optional[float] = None
    readability_score: Optional[float] = None
    average_sentence_length: Optional[float] = None
    average_word_length: Optional[float] = None
    total_authors: Optional[int] = None
    revision_authors: Optional[int] = None
    simplicity_score: Optional[float] = None
    content_snapshot: Optional[str] = None


class HistoricalMetricsCreate(HistoricalMetricsBase):
    """Schema for creating historical metrics"""
    agency_id: int
    document_id: int


class HistoricalMetricsUpdate(BaseModel):
    """Schema for updating historical metrics"""
    metrics_date: Optional[date] = None
    word_count: Optional[int] = None
    paragraph_count: Optional[int] = None
    sentence_count: Optional[int] = None
    section_count: Optional[int] = None
    subpart_count: Optional[int] = None
    language_complexity_score: Optional[float] = None
    readability_score: Optional[float] = None
    average_sentence_length: Optional[float] = None
    average_word_length: Optional[float] = None
    total_authors: Optional[int] = None
    revision_authors: Optional[int] = None
    simplicity_score: Optional[float] = None
    content_snapshot: Optional[str] = None


class HistoricalMetrics(HistoricalMetricsBase):
    """Schema for reading historical metrics"""
    id: int
    agency_id: int
    document_id: int

    class Config:
        orm_mode = True


class HistoricalMetricsList(BaseModel):
    """Schema for a list of historical metrics"""
    items: List[HistoricalMetrics]
    total: int


class ReadabilityMetrics(BaseModel):
    combined_score: float = Field(..., description="Combined weighted score from all readability metrics (0-100)")
    flesch_reading_ease: float = Field(..., description="Flesch Reading Ease score (0-100)")
    smog_index: float = Field(..., description="SMOG Index score normalized to 0-100")
    automated_readability: float = Field(..., description="Automated Readability Index normalized to 0-100")


class MetricsResponse(BaseModel):
    document_id: uuid.UUID
    metrics_date: datetime
    word_count: int
    sentence_count: int
    paragraph_count: int
    readability: ReadabilityMetrics
    
    class Config:
        from_attributes = True


class MetricsComputeRequest(BaseModel):
    agency_id: int
    content: Optional[str] = None
    document_content_id: Optional[uuid.UUID] = None
    metrics_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class MetricsDocumentRequest(BaseModel):
    document_id: uuid.UUID
    agency_id: int
    content: Optional[str] = None
    document_content_id: Optional[uuid.UUID] = None
    metrics_date: Optional[datetime] = None


class MetricsComputeBatchRequest(BaseModel):
    documents: List[MetricsDocumentRequest]
    
    class Config:
        from_attributes = True


class DocumentMetricsResult(BaseModel):
    document_id: uuid.UUID
    title: str
    metrics_date: datetime
    word_count: int
    sentence_count: int
    paragraph_count: int
    readability: ReadabilityMetrics


class DocumentError(BaseModel):
    document_id: uuid.UUID
    title: str
    error: str


class MetricsBatchResponse(BaseModel):
    total_processed: int = Field(..., description="Total number of documents processed")
    success_count: int = Field(..., description="Number of documents successfully processed")
    error_count: int = Field(..., description="Number of documents that failed processing")
    results: List[DocumentMetricsResult] = Field(..., description="Successfully processed documents")
    errors: List[DocumentError] = Field(..., description="Documents that failed processing")
    
    class Config:
        from_attributes = True 