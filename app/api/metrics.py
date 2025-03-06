from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import uuid

from app.database import get_db
from app.services.metrics_service import MetricsService
from app.models.document_content import DocumentContent
from app.models.agency import Agency
from app.schemas.metrics import (
    MetricsResponse,
    MetricsComputeRequest,
    MetricsBatchResponse
)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

@router.post("/compute/{document_id}", response_model=MetricsResponse)
async def compute_metrics(
    document_id: uuid.UUID,
    request: MetricsComputeRequest,
    db: Session = Depends(get_db)
):
    """
    Compute and store metrics for a specific document.
    Can compute from either raw content or an existing DocumentContent record.
    """
    try:
        metrics = MetricsService.compute_and_store_metrics(
            db=db,
            document_id=document_id,
            agency_id=request.agency_id,
            content=request.content,
            document_content_id=request.document_content_id,
            metrics_date=request.metrics_date
        )
        return MetricsResponse(
            document_id=document_id,
            metrics_date=metrics.metrics_date,
            word_count=metrics.word_count,
            sentence_count=metrics.sentence_count,
            paragraph_count=metrics.paragraph_count,
            readability={
                "combined_score": metrics.combined_readability_score,
                "flesch_reading_ease": metrics.flesch_reading_ease,
                "smog_index": metrics.smog_index_score,
                "automated_readability": metrics.automated_readability_score
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing metrics: {str(e)}")

@router.post("/compute-batch")
def compute_metrics_batch(workers: Optional[int] = 2, db: Session = Depends(get_db)):
    """
    Compute metrics for all documents that don't have metrics yet.
    Supports parallel processing with multiple workers (default=2, max=10).
    """
    try:
        return MetricsService.compute_metrics_for_all_documents(db=db, workers=workers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}", response_model=dict)
async def get_document_metrics(
    document_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Retrieve metrics for a document, optionally within a date range.
    """
    return MetricsService.get_document_metrics(
        db=db,
        document_id=document_id,
        start_date=start_date,
        end_date=end_date
    ) 