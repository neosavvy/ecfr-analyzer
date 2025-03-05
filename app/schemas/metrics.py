from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field


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