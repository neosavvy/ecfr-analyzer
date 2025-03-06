from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import update

from app.models.document import AgencyDocument
from app.models.agency import Agency
from app.utils.logging import get_logger

logger = get_logger(__name__)

class DocumentService:
    """Service for handling document operations"""
    
    @staticmethod
    def compute_and_backfill_agency_ids(db: Session) -> Tuple[int, int, List[str]]:
        """
        Compute and backfill agency_ids for all documents that don't have one.
        
        Returns:
            Tuple containing:
            - Number of documents processed
            - Number of documents updated
            - List of errors
        """
        logger.info("Starting agency ID backfill")
        
        # Get all documents without agency_id
        documents = db.query(AgencyDocument).filter(
            AgencyDocument.agency_id == None
        ).all()
        
        total_processed = len(documents)
        updated_count = 0
        errors = []
        
        for doc in documents:
            try:
                # Try to extract agency_id from metadata
                agency_id = AgencyDocument.extract_agency_id_from_metadata(doc.agency_metadata)
                
                if agency_id:
                    # Verify agency exists
                    agency = db.query(Agency).filter(Agency.id == agency_id).first()
                    if agency:
                        doc.agency_id = agency_id
                        updated_count += 1
                    else:
                        errors.append(f"Document {doc.id}: Agency {agency_id} not found")
                else:
                    errors.append(f"Document {doc.id}: Could not extract agency_id from metadata")
            
            except Exception as e:
                error_msg = f"Document {doc.id}: Error processing - {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Commit all changes
        if updated_count > 0:
            try:
                db.commit()
                logger.info(f"Successfully updated {updated_count} documents")
            except Exception as e:
                logger.error(f"Error committing changes: {str(e)}")
                db.rollback()
                errors.append(f"Failed to commit changes: {str(e)}")
                updated_count = 0
        
        return total_processed, updated_count, errors
    
    @staticmethod
    def verify_agency_ids(db: Session) -> Tuple[int, List[str]]:
        """
        Verify that all documents have valid agency IDs.
        
        Returns:
            Tuple containing:
            - Number of documents with valid agency IDs
            - List of error messages for invalid documents
        """
        logger.info("Starting agency ID verification")
        
        # Get all documents
        documents = db.query(AgencyDocument).all()
        valid_count = 0
        errors = []
        
        for doc in documents:
            if not doc.agency_id:
                errors.append(f"Document {doc.id}: Missing agency_id")
                continue
                
            # Verify agency exists
            agency = db.query(Agency).filter(Agency.id == doc.agency_id).first()
            if not agency:
                errors.append(f"Document {doc.id}: Invalid agency_id {doc.agency_id}")
                continue
                
            valid_count += 1
        
        return valid_count, errors 