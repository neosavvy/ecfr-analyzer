from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, cast, JSON, text
from sqlalchemy.dialects.postgresql import JSONB
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.database import SessionLocal

from app.models.metrics import AgencyRegulationDocumentHistoricalMetrics
from app.models.document_content import DocumentContent
from app.models.document import AgencyDocument
from app.models.search_descriptor import AgencyTitleSearchDescriptor
from app.services.xml_processor import XMLProcessor
from app.utils.logging import get_logger

logger = get_logger(__name__)

class MetricsService:
    """Service for computing and storing document metrics"""
    
    @staticmethod
    def process_document_batch(doc_batch: List[Tuple[AgencyDocument, DocumentContent]]) -> List[Dict[str, Any]]:
        """Process a batch of documents using a separate database session."""
        db = SessionLocal()
        try:
            results = []
            for doc, content in doc_batch:
                try:
                    logger.debug(f"Processing document {doc.id}")
                    content_to_process = content.processed_text
                    content_source = "processed_text"
                    
                    if not content_to_process and content.raw_xml:
                        logger.info(f"Falling back to raw XML for document {doc.id}")
                        content_to_process = content.raw_xml
                        content_source = "raw_xml"
                    
                    if not content_to_process:
                        raise ValueError("Document has neither processed text nor raw XML available")
                        
                    metrics = MetricsService.compute_and_store_metrics(
                        db=db,
                        document_id=doc.id,
                        agency_id=doc.agency_id,
                        content=content_to_process,
                        metrics_date=content.version_date
                    )
                    
                    results.append({
                        "success": True,
                        "document_id": doc.id,
                        "title": doc.title,
                        "metrics_date": metrics.metrics_date,
                        "content_source": content_source,
                        "word_count": metrics.word_count,
                        "sentence_count": metrics.sentence_count,
                        "paragraph_count": metrics.paragraph_count,
                        "readability": {
                            "combined_score": metrics.combined_readability_score,
                            "flesch_reading_ease": metrics.flesch_reading_ease,
                            "smog_index": metrics.smog_index_score,
                            "automated_readability": metrics.automated_readability_score
                        }
                    })
                    
                except Exception as e:
                    error_msg = f"Error processing document {doc.id}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    results.append({
                        "success": False,
                        "document_id": doc.id,
                        "title": doc.title,
                        "error": str(e),
                        "content_status": (
                            "no_content" if not content.processed_text and not content.raw_xml
                            else "error_during_processing"
                        ),
                        "attempted_source": content_source if 'content_source' in locals() else None
                    })
            return results
        finally:
            db.close()
    
    @staticmethod
    def compute_metrics_for_all_documents(
        db: Session,
        agency_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None,
        workers: int = 2
    ) -> Dict[str, Any]:
        """
        Find all documents that need metrics computed and process them using parallel workers.
        
        Args:
            db: Database session
            agency_id: Optional agency ID to filter by
            start_date: Optional start date for document versions
            end_date: Optional end date for document versions
            limit: Optional limit on number of documents to process
            workers: Number of worker threads (default=2, max=10)
            
        Returns:
            Dictionary containing results summary and processed documents
        """
        # Validate and cap workers
        workers = max(1, min(10, workers))
        logger.info(f"Starting batch metrics computation with {workers} workers")
        
        # First, get count of existing metrics
        existing_metrics_count = db.query(AgencyRegulationDocumentHistoricalMetrics).count()
        logger.info(f"Current metrics count in database: {existing_metrics_count}")
        
        # Find documents that need processing
        query = (
            db.query(AgencyDocument, DocumentContent)
            .join(
                AgencyTitleSearchDescriptor,
                AgencyTitleSearchDescriptor.agency_id == AgencyDocument.agency_id
            )
            .join(
                DocumentContent,
                DocumentContent.descriptor_id == AgencyTitleSearchDescriptor.id
            )
            .filter(or_(
                DocumentContent.processed_text != None,
                DocumentContent.raw_xml != None
            ))
            .outerjoin(
                AgencyRegulationDocumentHistoricalMetrics,
                and_(
                    AgencyRegulationDocumentHistoricalMetrics.document_id == AgencyDocument.id,
                    AgencyRegulationDocumentHistoricalMetrics.metrics_date == DocumentContent.version_date
                )
            )
            .filter(AgencyRegulationDocumentHistoricalMetrics.id == None)
            .filter(AgencyDocument.agency_id != None)
            .group_by(AgencyDocument.id, DocumentContent.id)
        )
        
        # Apply filters
        if agency_id:
            query = query.filter(AgencyDocument.agency_id == agency_id)
        if start_date:
            query = query.filter(DocumentContent.version_date >= start_date)
        if end_date:
            query = query.filter(DocumentContent.version_date <= end_date)
        if limit:
            query = query.limit(limit)
            
        # Get documents to process
        documents_to_process = query.all()
        total_documents = len(documents_to_process)
        logger.info(f"Found {total_documents} documents to process")
        
        if not total_documents:
            return {
                "total_processed": 0,
                "success_count": 0,
                "error_count": 0,
                "results": [],
                "errors": []
            }
            
        # Adjust workers if we have fewer documents than workers
        workers = min(workers, total_documents)
        logger.info(f"Using {workers} workers for {total_documents} documents")
        
        # Calculate batch size and create batches
        batch_size = (total_documents + workers - 1) // workers  # Ceiling division
        document_batches = []
        
        for i in range(workers):
            start_idx = i * batch_size
            end_idx = min(start_idx + batch_size, total_documents)
            if start_idx < end_idx:  # Only create batch if there are documents left
                document_batches.append(documents_to_process[start_idx:end_idx])
        
        logger.info(f"Created {len(document_batches)} batches of approximately {batch_size} documents each")
        
        # Process batches in parallel
        results = []
        success_count = 0
        error_count = 0
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_batch = {
                executor.submit(MetricsService.process_document_batch, batch): i
                for i, batch in enumerate(document_batches)
            }
            
            for future in as_completed(future_to_batch):
                batch_results = future.result()
                for result in batch_results:
                    if result.get("success", False):
                        success_count += 1
                        results.append(result)
                    else:
                        error_count += 1
                        results.append(result)
        
        logger.info(f"Completed batch processing with {workers} workers. Successes: {success_count}, Errors: {error_count}")
        
        # Separate successful results and errors
        successful_results = [r for r in results if r.get("success", False)]
        error_results = [r for r in results if not r.get("success", False)]
        
        return {
            "total_processed": total_documents,
            "success_count": success_count,
            "error_count": error_count,
            "results": successful_results,
            "errors": error_results
        }
    
    @staticmethod
    def compute_and_store_metrics(
        db: Session,
        document_id: uuid.UUID,
        agency_id: int,
        content: Optional[str] = None,
        document_content_id: Optional[uuid.UUID] = None,
        metrics_date: Optional[datetime] = None
    ) -> AgencyRegulationDocumentHistoricalMetrics:
        """
        Compute metrics for a document and store them in the database.
        Either content or document_content_id must be provided.
        """
        if not content and not document_content_id:
            raise ValueError("Either content or document_content_id must be provided")
            
        # If no content provided, fetch it from DocumentContent
        if not content and document_content_id:
            doc_content = db.query(DocumentContent).filter(
                DocumentContent.id == document_content_id
            ).first()
            if not doc_content:
                raise ValueError(f"No DocumentContent found with id {document_content_id}")
            content = doc_content.processed_text or doc_content.raw_xml
            
        # Use current date if none provided
        if not metrics_date:
            metrics_date = datetime.now()
            
        # Clean and validate content
        if not content or not isinstance(content, str):
            raise ValueError("Invalid content: must be a non-empty string")
        
        content = content.strip()
        if not content:
            raise ValueError("Content is empty after stripping whitespace")
            
        # Check if metrics already exist for this document/date
        existing_metrics = db.query(AgencyRegulationDocumentHistoricalMetrics).filter(
            and_(
                AgencyRegulationDocumentHistoricalMetrics.document_id == document_id,
                AgencyRegulationDocumentHistoricalMetrics.metrics_date == metrics_date
            )
        ).first()
        
        if existing_metrics:
            logger.info(f"Metrics already exist for document {document_id} on {metrics_date}")
            return existing_metrics
        
        # Compute metrics
        metrics = XMLProcessor.analyze_content(content)
        
        # Create metrics record
        historical_metrics = AgencyRegulationDocumentHistoricalMetrics(
            metrics_date=metrics_date,
            document_id=document_id,
            agency_id=agency_id,
            
            # Basic metrics
            word_count=metrics["word_count"],
            sentence_count=metrics["sentence_count"],
            paragraph_count=metrics["paragraph_count"],
            
            # Readability scores
            combined_readability_score=metrics["readability_score"],
            flesch_reading_ease=metrics["readability_metrics"]["flesch_reading_ease"],
            smog_index_score=metrics["readability_metrics"]["smog_index"],
            automated_readability_score=metrics["readability_metrics"]["automated_readability_index"]
        )
        
        try:
            db.add(historical_metrics)
            db.commit()
            db.refresh(historical_metrics)
            return historical_metrics
        except Exception as e:
            db.rollback()
            raise ValueError(f"Failed to store metrics: {str(e)}")
    
    @staticmethod
    def get_document_metrics(
        db: Session,
        document_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Retrieve metrics for a document within a date range.
        If no date range provided, returns the latest metrics.
        """
        query = db.query(AgencyRegulationDocumentHistoricalMetrics).filter(
            AgencyRegulationDocumentHistoricalMetrics.document_id == document_id
        )
        
        if start_date:
            query = query.filter(AgencyRegulationDocumentHistoricalMetrics.metrics_date >= start_date)
        if end_date:
            query = query.filter(AgencyRegulationDocumentHistoricalMetrics.metrics_date <= end_date)
            
        # Order by date descending
        query = query.order_by(AgencyRegulationDocumentHistoricalMetrics.metrics_date.desc())
        
        metrics = query.all()
        
        return {
            "document_id": document_id,
            "metrics": [
                {
                    "date": metric.metrics_date,
                    "word_count": metric.word_count,
                    "sentence_count": metric.sentence_count,
                    "paragraph_count": metric.paragraph_count,
                    "readability": {
                        "combined_score": metric.combined_readability_score,
                        "flesch_reading_ease": metric.flesch_reading_ease,
                        "smog_index": metric.smog_index_score,
                        "automated_readability": metric.automated_readability_score
                    }
                }
                for metric in metrics
            ]
        } 