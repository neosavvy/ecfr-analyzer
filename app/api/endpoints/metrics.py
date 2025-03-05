from typing import List, Optional
from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.crud import metrics as metrics_crud
from app.schemas.metrics import (
    HistoricalMetrics,
    HistoricalMetricsCreate,
    HistoricalMetricsUpdate,
    HistoricalMetricsList
)

router = APIRouter()


@router.get("/{metrics_id}", response_model=HistoricalMetrics)
def get_metrics(
    metrics_id: UUID = Path(..., description="The ID of the metrics to retrieve"),
    db: Session = Depends(get_db)
):
    """
    Retrieve historical metrics by ID.
    """
    db_metrics = metrics_crud.get_historical_metrics(db, metrics_id)
    if db_metrics is None:
        raise HTTPException(status_code=404, detail="Historical metrics not found")
    return db_metrics


@router.get("/document/{document_id}", response_model=HistoricalMetricsList)
def get_document_metrics(
    document_id: UUID = Path(..., description="The ID of the document"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Retrieve all historical metrics for a specific document.
    """
    metrics_list = metrics_crud.get_historical_metrics_by_document(db, document_id, skip, limit)
    total = metrics_crud.get_metrics_count(db)
    return {"items": metrics_list, "total": total}


@router.get("/document/{document_id}/date/{metrics_date}", response_model=HistoricalMetrics)
def get_document_metrics_by_date(
    document_id: UUID = Path(..., description="The ID of the document"),
    metrics_date: date = Path(..., description="The date of the metrics (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Retrieve historical metrics for a specific document and date.
    """
    db_metrics = metrics_crud.get_historical_metrics_by_document_and_date(db, document_id, metrics_date)
    if db_metrics is None:
        raise HTTPException(status_code=404, detail="Historical metrics not found for this document and date")
    return db_metrics


@router.get("/agency/{agency_id}", response_model=HistoricalMetricsList)
def get_agency_metrics(
    agency_id: UUID = Path(..., description="The ID of the agency"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Retrieve all historical metrics for a specific agency.
    """
    metrics_list = metrics_crud.get_historical_metrics_by_agency(db, agency_id, skip, limit)
    total = metrics_crud.get_metrics_count(db)
    return {"items": metrics_list, "total": total}


@router.post("/", response_model=HistoricalMetrics)
def create_metrics(
    metrics: HistoricalMetricsCreate,
    db: Session = Depends(get_db)
):
    """
    Create new historical metrics.
    """
    # Check if metrics already exist for this document and date
    existing_metrics = metrics_crud.get_historical_metrics_by_document_and_date(
        db, metrics.document_id, metrics.metrics_date
    )
    if existing_metrics:
        raise HTTPException(
            status_code=400, 
            detail="Historical metrics already exist for this document and date"
        )
    
    return metrics_crud.create_historical_metrics(db, metrics)


@router.put("/{metrics_id}", response_model=HistoricalMetrics)
def update_metrics(
    metrics: HistoricalMetricsUpdate,
    metrics_id: UUID = Path(..., description="The ID of the metrics to update"),
    db: Session = Depends(get_db)
):
    """
    Update historical metrics.
    """
    db_metrics = metrics_crud.update_historical_metrics(db, metrics_id, metrics)
    if db_metrics is None:
        raise HTTPException(status_code=404, detail="Historical metrics not found")
    return db_metrics


@router.delete("/{metrics_id}", response_model=bool)
def delete_metrics(
    metrics_id: UUID = Path(..., description="The ID of the metrics to delete"),
    db: Session = Depends(get_db)
):
    """
    Delete historical metrics.
    """
    success = metrics_crud.delete_historical_metrics(db, metrics_id)
    if not success:
        raise HTTPException(status_code=404, detail="Historical metrics not found")
    return success 