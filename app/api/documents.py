from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.database import get_db
from app.services.document_service import DocumentService

router = APIRouter(prefix="/api/documents", tags=["documents"])

@router.post("/compute-agency-ids", response_model=Dict[str, Any])
async def compute_agency_ids(
    db: Session = Depends(get_db)
):
    """
    Compute and backfill agency IDs for all documents that don't have one.
    This is a maintenance endpoint to help with data migration.
    """
    try:
        total_processed, updated_count, errors = DocumentService.compute_and_backfill_agency_ids(db)
        
        return {
            "status": "completed",
            "total_processed": total_processed,
            "updated_count": updated_count,
            "error_count": len(errors),
            "errors": errors
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing agency IDs: {str(e)}")

@router.get("/verify-agency-ids", response_model=Dict[str, Any])
async def verify_agency_ids(
    db: Session = Depends(get_db)
):
    """
    Verify that all documents have valid agency IDs.
    """
    try:
        valid_count, errors = DocumentService.verify_agency_ids(db)
        
        return {
            "status": "completed",
            "valid_count": valid_count,
            "error_count": len(errors),
            "errors": errors
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying agency IDs: {str(e)}") 