from typing import List, Optional, Dict, Any, Union
from datetime import date
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.models.metrics import AgencyRegulationDocumentHistoricalMetrics
from app.schemas.metrics import HistoricalMetricsCreate, HistoricalMetricsUpdate


def get_historical_metrics(db: Session, metrics_id: UUID) -> Optional[AgencyRegulationDocumentHistoricalMetrics]:
    """Get historical metrics by ID"""
    return db.query(AgencyRegulationDocumentHistoricalMetrics).filter(
        AgencyRegulationDocumentHistoricalMetrics.id == metrics_id
    ).first()


def get_historical_metrics_by_document(
    db: Session, 
    document_id: UUID, 
    skip: int = 0, 
    limit: int = 100
) -> List[AgencyRegulationDocumentHistoricalMetrics]:
    """Get all historical metrics for a specific document"""
    return db.query(AgencyRegulationDocumentHistoricalMetrics).filter(
        AgencyRegulationDocumentHistoricalMetrics.document_id == document_id
    ).order_by(desc(AgencyRegulationDocumentHistoricalMetrics.metrics_date)).offset(skip).limit(limit).all()


def get_historical_metrics_by_document_and_date(
    db: Session, 
    document_id: UUID, 
    metrics_date: date
) -> Optional[AgencyRegulationDocumentHistoricalMetrics]:
    """Get historical metrics for a specific document and date"""
    return db.query(AgencyRegulationDocumentHistoricalMetrics).filter(
        and_(
            AgencyRegulationDocumentHistoricalMetrics.document_id == document_id,
            AgencyRegulationDocumentHistoricalMetrics.metrics_date == metrics_date
        )
    ).first()


def get_historical_metrics_by_agency(
    db: Session, 
    agency_id: UUID, 
    skip: int = 0, 
    limit: int = 100
) -> List[AgencyRegulationDocumentHistoricalMetrics]:
    """Get all historical metrics for a specific agency"""
    return db.query(AgencyRegulationDocumentHistoricalMetrics).filter(
        AgencyRegulationDocumentHistoricalMetrics.agency_id == agency_id
    ).order_by(desc(AgencyRegulationDocumentHistoricalMetrics.metrics_date)).offset(skip).limit(limit).all()


def create_historical_metrics(
    db: Session, 
    metrics: HistoricalMetricsCreate
) -> AgencyRegulationDocumentHistoricalMetrics:
    """Create new historical metrics"""
    db_metrics = AgencyRegulationDocumentHistoricalMetrics(**metrics.dict())
    db.add(db_metrics)
    db.commit()
    db.refresh(db_metrics)
    return db_metrics


def update_historical_metrics(
    db: Session, 
    metrics_id: UUID, 
    metrics: HistoricalMetricsUpdate
) -> Optional[AgencyRegulationDocumentHistoricalMetrics]:
    """Update historical metrics"""
    db_metrics = get_historical_metrics(db, metrics_id)
    if not db_metrics:
        return None
    
    update_data = metrics.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_metrics, key, value)
    
    db.commit()
    db.refresh(db_metrics)
    return db_metrics


def delete_historical_metrics(db: Session, metrics_id: UUID) -> bool:
    """Delete historical metrics"""
    db_metrics = get_historical_metrics(db, metrics_id)
    if not db_metrics:
        return False
    
    db.delete(db_metrics)
    db.commit()
    return True


def get_metrics_count(db: Session) -> int:
    """Get total count of historical metrics records"""
    return db.query(AgencyRegulationDocumentHistoricalMetrics).count() 