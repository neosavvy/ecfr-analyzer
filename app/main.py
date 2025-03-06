from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

import os
import time
from typing import List


from app.api.agencies import router as agencies_router
from app.api.metrics import router as metrics_router
from app.api.documents import router as documents_router
from app.database import get_db, SessionLocal
from app.models.agency import Agency
from app.models.search_descriptor import AgencyTitleSearchDescriptor
from app.models.document_content import DocumentContent
from app.services.ecfr_api import ECFRApiClient
from app.services.xml_processor import XMLProcessor
from app.models.agency_document_count import AgencyDocumentCount
from app.models.metrics import AgencyRegulationDocumentHistoricalMetrics
from app.models.document import AgencyDocument
from app.utils.logging import configure_logging, get_logger, TRACE, DEBUG, INFO

# Get the logger for this module
logger = get_logger(__name__)

# Configure logging based on environment variable
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
if log_level == "TRACE":
    configure_logging(TRACE)
elif log_level == "DEBUG":
    configure_logging(DEBUG)
else:
    configure_logging(INFO)

app = FastAPI(title="eCFR Analyzer", description="API for analyzing the Electronic Code of Federal Regulations")
logger.info("eCFR Analyzer API initialized")

# Include routers
app.include_router(agencies_router)
app.include_router(metrics_router)
app.include_router(documents_router)

@app.get("/")
async def root():
    return {"message": "Welcome to eCFR Analyzer API"}

# Include the agencies router
app.include_router(agencies_router, prefix="/api/agencies", tags=["agencies"])

@app.get("/api/agencies/{agency_slug}/documents")
async def get_agency_documents(
    agency_slug: str, 
    start_page: int = None,
    per_page: int = 20, 
    reset: bool = False,
    process_all: bool = False,
    max_pages: int = None,
    target_year: int = None,
    db: Session = Depends(get_db)
):
    """
    Retrieve documents for a given agency and store them in the database.
    
    Args:
        agency_slug: The slug of the agency
        start_page: The page to start from (if None, will resume from last page or start from 0)
        per_page: Number of results per page
        reset: If True, will reset pagination and start from page 0
        process_all: If True, will process all pages until completion
        max_pages: Maximum number of pages to process in a single request (only used with process_all=True)
        target_year: If provided, will only fetch documents modified in the specified year
    """
    logger.info(f"Starting get_agency_documents for agency_slug={agency_slug}, start_page={start_page}, per_page={per_page}, target_year={target_year}")
    
    # Get the agency
    agency = db.query(Agency).filter(Agency.slug == agency_slug).first()
    if not agency:
        logger.error(f"Agency with slug '{agency_slug}' not found")
        raise HTTPException(status_code=404, detail=f"Agency with slug '{agency_slug}' not found")
    
    logger.debug(f"Found agency: {agency.name} (ID: {agency.id})")
    
    # Initialize API client
    ecfr_client = ECFRApiClient()
    
    # Set up date range parameters if target_year is provided
    last_modified_on_or_after = None
    last_modified_before = None
    
    # Check if we have an existing count record
    count_record = db.query(AgencyDocumentCount).filter(
        AgencyDocumentCount.agency_id == agency.id,
        AgencyDocumentCount.is_complete < 2  # Not complete
    ).order_by(AgencyDocumentCount.query_date.desc()).first()
    
    # Use target_year from count_record if it exists and no target_year is provided
    if count_record and count_record.target_year and not target_year:
        target_year = count_record.target_year
        logger.info(f"Using target_year {target_year} from existing count record")
    
    # Set up date range parameters based on target_year
    if target_year:
        last_modified_on_or_after = f"{target_year-1}-01-01"
        last_modified_before = f"{target_year}-01-01"
        logger.info(f"Using date range: {last_modified_on_or_after} to {last_modified_before}")
    
    # Get document count
    logger.debug(f"Fetching document count for agency '{agency_slug}'")
    count_data = ecfr_client.get_agency_document_count(
        agency_slug, 
        last_modified_on_or_after=last_modified_on_or_after,
        last_modified_before=last_modified_before
    )
    total_count = count_data.get("meta", {}).get("total_count", 0)
    logger.info(f"Agency '{agency.name}' has {total_count} documents")
    
    # Determine the starting page
    current_page = 0
    if reset:
        logger.info(f"Resetting pagination for agency '{agency.name}'")
        # Reset pagination
        if count_record:
            count_record.current_page = 0
            count_record.is_complete = 0
    elif start_page is not None:
        logger.info(f"Starting from specified page {start_page} for agency '{agency.name}'")
        # Use the specified page
        current_page = start_page
        if count_record:
            count_record.current_page = start_page
    elif count_record:
        logger.info(f"Resuming from last page {count_record.current_page} for agency '{agency.name}'")
        # Resume from last page
        current_page = count_record.current_page
    
    # Create a new count record if needed
    if not count_record or reset:
        logger.info(f"Creating new count record for agency '{agency.name}'")
        today = datetime.now().date()
        count_record = AgencyDocumentCount(
            agency_id=agency.id,
            reference_date=today,
            total_count=total_count,
            current_page=current_page,
            per_page=per_page,
            is_complete=1,  # Mark as in progress
            target_year=target_year  # Save the target year
        )
        db.add(count_record)
        logger.trace(f"Added new count record to session: {count_record}")
    
    # Calculate total pages
    total_pages = (total_count + per_page - 1) // per_page
    logger.debug(f"Total pages: {total_pages}")
    
    # Check if we're done
    if current_page >= total_pages:
        logger.info(f"All documents for agency '{agency.name}' have been processed")
        count_record.is_complete = 2  # Mark as complete
        db.commit()
        logger.debug("Committed changes to database")
        return {
            "message": f"All documents for agency '{agency.name}' have been processed",
            "total_count": total_count,
            "total_pages": total_pages,
            "current_page": current_page,
            "status": "complete"
        }
    
    # Initialize counters for all pages
    total_results_added = 0
    total_descriptors_added = 0
    pages_processed = 0
    
    # Process pages until completion or until max_pages is reached
    while current_page < total_pages:
        if max_pages is not None and pages_processed >= max_pages:
            logger.info(f"Reached maximum pages limit ({max_pages})")
            break
            
        # Process the current page
        logger.info(f"Processing page {current_page + 1} of {total_pages} for agency '{agency.name}'")
        search_results = ecfr_client.search_agency_documents(
            agency_slug, 
            page=current_page + 1, 
            per_page=per_page,
            last_modified_on_or_after=last_modified_on_or_after,
            last_modified_before=last_modified_before
        )
        
        # Process and store search results
        results_added = 0
        descriptors_added = 0
        
        if "results" in search_results:
            logger.debug(f"Found {len(search_results['results'])} results on page {current_page + 1}")
            for i, result in enumerate(search_results["results"]):
                logger.trace(f"Processing result {i+1}/{len(search_results['results'])} on page {current_page + 1}")
                
                # Create or update search descriptor
                existing_descriptor = None
                
                # Check if we can identify the descriptor by structure_index
                if "structure_index" in result:
                    logger.trace(f"Looking for existing descriptor with structure_index={result['structure_index']}")
                    existing_descriptor = db.query(AgencyTitleSearchDescriptor).filter(
                        AgencyTitleSearchDescriptor.agency_id == agency.id,
                        AgencyTitleSearchDescriptor.structure_index == result["structure_index"]
                    ).first()
                
                if existing_descriptor:
                    logger.trace(f"Updating existing descriptor: {existing_descriptor.id}")
                    # Update existing descriptor
                    for key, value in result.items():
                        setattr(existing_descriptor, key, value)
                    descriptor = existing_descriptor
                else:
                    logger.trace(f"Creating new descriptor from result")
                    # Create new descriptor
                    descriptor = AgencyTitleSearchDescriptor.from_api_response(result, agency.id)
                    db.add(descriptor)
                    descriptors_added += 1
                    logger.trace(f"Added new descriptor to session")
                
                logger.trace(f"Flushing session to get descriptor ID")
                db.flush()  # Flush to get the ID
                logger.trace(f"Descriptor ID: {descriptor.id}")
                
                # Get document content if hierarchy has title and chapter
                if descriptor.hierarchy and descriptor.hierarchy.get("title") and descriptor.hierarchy.get("chapter"):
                    # Use the descriptor's date instead of today's date
                    # First try ends_on, then starts_on, then fall back to today
                    content_date = None
                    
                    if descriptor.ends_on:
                        # Check if ends_on is already a string
                        if isinstance(descriptor.ends_on, str):
                            content_date = descriptor.ends_on
                        else:
                            # If it's a date object, format it
                            content_date = descriptor.ends_on.strftime("%Y-%m-%d")
                    elif descriptor.starts_on:
                        # Check if starts_on is already a string
                        if isinstance(descriptor.starts_on, str):
                            content_date = descriptor.starts_on
                        else:
                            # If it's a date object, format it
                            content_date = descriptor.starts_on.strftime("%Y-%m-%d")
                    else:
                        # If no dates are available, use today's date
                        content_date = datetime.now().strftime("%Y-%m-%d")
                    
                    logger.debug(f"Using date {content_date} for document content retrieval")
                    
                    logger.trace(f"Fetching XML content for title={descriptor.hierarchy['title']}, chapter={descriptor.hierarchy.get('chapter')}")
                    xml_content = ecfr_client.get_document_content(
                        content_date,
                        descriptor.hierarchy["title"],
                        chapter=descriptor.hierarchy.get("chapter"),
                        part=descriptor.hierarchy.get("part"),
                        section=descriptor.hierarchy.get("section"),
                        appendix=descriptor.hierarchy.get("appendix")
                    )
                    
                    if xml_content:
                        logger.trace(f"Received XML content of length {len(xml_content)}")
                        # Check if we already have this content
                        # Parse the content_date string to a date object if needed
                        version_date = None
                        if isinstance(content_date, str):
                            try:
                                version_date = datetime.strptime(content_date, "%Y-%m-%d").date()
                            except ValueError:
                                # If the date format is invalid, use today's date
                                logger.warning(f"Invalid date format: {content_date}, using today's date instead")
                                version_date = datetime.now().date()
                        else:
                            version_date = content_date
                            
                        logger.trace(f"Checking for existing content with descriptor_id={descriptor.id}, version_date={version_date}")
                        existing_content = db.query(DocumentContent).filter(
                            DocumentContent.descriptor_id == descriptor.id,
                            DocumentContent.version_date == version_date
                        ).first()
                        
                        if not existing_content:
                            logger.trace(f"Processing XML content")
                            # Process the XML content
                            processed_text = XMLProcessor.extract_text_from_xml(xml_content)
                            
                            logger.trace(f"Creating new document content")
                            # Create document content
                            content = DocumentContent(
                                descriptor_id=descriptor.id,
                                agency_id=agency.id,
                                version_date=version_date,
                                raw_xml=xml_content,
                                processed_text=processed_text
                            )
                            db.add(content)
                            db.flush()  # Flush to get the content ID
                            
                            # Create or get AgencyDocument record
                            document_title = f"Title {descriptor.hierarchy['title']}"
                            if descriptor.hierarchy.get('chapter'):
                                document_title += f", Chapter {descriptor.hierarchy['chapter']}"
                            if descriptor.hierarchy.get('part'):
                                document_title += f", Part {descriptor.hierarchy['part']}"
                            
                            document_id_str = f"T{descriptor.hierarchy['title']}"
                            if descriptor.hierarchy.get('chapter'):
                                document_id_str += f"C{descriptor.hierarchy['chapter']}"
                            if descriptor.hierarchy.get('part'):
                                document_id_str += f"P{descriptor.hierarchy['part']}"
                            
                            # Check if document already exists
                            existing_document = db.query(AgencyDocument).filter(
                                AgencyDocument.document_id == document_id_str,
                                AgencyDocument.agency_id == agency.id
                            ).first()
                            
                            if not existing_document:
                                # Create new document
                                document = AgencyDocument(
                                    title=document_title,
                                    document_id=document_id_str,
                                    agency_id=agency.id,
                                    agency_metadata=descriptor.hierarchy,
                                    created_at=datetime.now(),
                                    updated_at=datetime.now()
                                )
                                db.add(document)
                                db.flush()  # Flush to get the document ID
                                logger.trace(f"Created new AgencyDocument with ID {document.id}")
                            else:
                                document = existing_document
                                document.updated_at = datetime.now()
                                logger.trace(f"Using existing AgencyDocument with ID {document.id}")
                            
                            # Compute and save metrics
                            compute_xml_metrics(content, agency.id, db)
                            
                            logger.trace(f"Added new document content to session")
                            results_added += 1
                        else:
                            logger.trace(f"Content already exists, skipping")
                    else:
                        logger.warning(f"Failed to retrieve XML content for descriptor {descriptor.id}")
                else:
                    logger.trace(f"Descriptor doesn't have required hierarchy information, skipping content retrieval")
            
            logger.info(f"Added {descriptors_added} descriptors and {results_added} document contents on page {current_page + 1}")
        else:
            logger.warning(f"No results found on page {current_page + 1}")
        
        # Update counters
        total_results_added += results_added
        total_descriptors_added += descriptors_added
        pages_processed += 1
        
        # Update the count record
        current_page += 1
        count_record.current_page = current_page
        
        logger.debug(f"Committing changes for page {current_page}")
        # Commit changes for this page
        try:
            db.commit()
            logger.debug(f"Successfully committed changes for page {current_page}")
        except Exception as e:
            logger.error(f"Error committing changes for page {current_page}: {str(e)}")
            db.rollback()
            logger.debug("Rolled back transaction")
        
        # If not processing all pages, break after the first page
        if not process_all:
            logger.info(f"Not processing all pages, stopping after page {current_page}")
            break
    
    # Check if we've completed all pages
    if current_page >= total_pages:
        logger.info(f"Completed all pages for agency '{agency.name}'")
        count_record.is_complete = 2  # Mark as complete
        db.commit()
        logger.debug("Committed final changes to database")
    
    # Determine if there are more pages
    has_more = current_page < total_pages
    
    return {
        "message": f"Retrieved and stored documents for agency '{agency.name}'",
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": current_page,
        "pages_processed": pages_processed,
        "documents_found": len(search_results.get("results", [])) * pages_processed if "results" in search_results else 0,
        "descriptors_added": total_descriptors_added,
        "documents_stored": total_results_added,
        "has_more": has_more,
        "status": "complete" if not has_more else "in_progress",
        "next_page": current_page if has_more else None
    }

@app.get("/api/agencies/{agency_slug}/documents/status")
async def get_document_fetch_status(
    agency_slug: str,
    db: Session = Depends(get_db)
):
    """Get the status of the background document fetch task"""
    # Get the agency
    agency = db.query(Agency).filter(Agency.slug == agency_slug).first()
    if not agency:
        raise HTTPException(status_code=404, detail=f"Agency with slug '{agency_slug}' not found")
    
    # Get the latest count record
    count_record = db.query(AgencyDocumentCount).filter(
        AgencyDocumentCount.agency_id == agency.id
    ).order_by(AgencyDocumentCount.query_date.desc()).first()
    
    if not count_record:
        return {
            "message": f"No document fetch has been started for agency '{agency.name}'",
            "status": "not_started"
        }
    
    # Calculate progress
    total_pages = (count_record.total_count + count_record.per_page - 1) // count_record.per_page
    progress_percent = (count_record.current_page / total_pages) * 100 if total_pages > 0 else 0
    
    status = "not_started"
    if count_record.is_complete == 2:
        status = "complete"
    elif count_record.is_complete == 1:
        status = "in_progress"
    
    return {
        "message": f"Document fetch for agency '{agency.name}' is {status}",
        "status": status,
        "total_count": count_record.total_count,
        "total_pages": total_pages,
        "current_page": count_record.current_page,
        "progress_percent": round(progress_percent, 2),
        "last_updated": count_record.query_date.isoformat(),
        "estimated_remaining_pages": max(0, total_pages - count_record.current_page)
    }

@app.get("/api/agencies/{agency_slug}/documents/failed")
async def process_failed_documents(
    agency_slug: str,
    db: Session = Depends(get_db)
):
    """Process failed documents for a given agency"""
    logger = get_logger("failed_processor")
    logger.info(f"Starting to process failed documents for agency '{agency_slug}'")
    
    # Create a new database session
    db = SessionLocal()
    
    try:
        # Get the agency
        agency = db.query(Agency).filter(Agency.slug == agency_slug).first()
        if not agency:
            raise HTTPException(status_code=404, detail=f"Agency with slug '{agency_slug}' not found")
        
        agency_id = agency.id
        
        # Get all failed descriptors
        failed_descriptors = db.query(AgencyTitleSearchDescriptor).filter(
            AgencyTitleSearchDescriptor.agency_id == agency_id,
            AgencyTitleSearchDescriptor.processing_status == 0  # reset to not processed
        ).all()
        
        logger.info(f"Found {len(failed_descriptors)} documents to retry")
        
        # Initialize API client
        ecfr_client = ECFRApiClient()
        
        # Process each descriptor
        for i, descriptor in enumerate(failed_descriptors):
            logger.info(f"Processing descriptor {i+1}/{len(failed_descriptors)}")
            
            # Mark as processing
            descriptor.processing_status = 1
            db.commit()
            
            # Get document content
            content_added = get_and_store_document_content(descriptor, agency_id, db, ecfr_client)
            
            # Commit changes
            db.commit()
            
            # Add a small delay to avoid rate limiting
            time.sleep(1)
        
        logger.info(f"Completed processing failed documents for agency '{agency_slug}'")
        
        return {
            "message": f"Processed {len(failed_descriptors)} failed documents for agency '{agency.name}'",
            "documents_processed": len(failed_descriptors)
        }
    
    except Exception as e:
        logger.error(f"Error processing failed documents: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing failed documents: {str(e)}")
    
    finally:
        db.close()

def get_and_store_document_content(descriptor, agency_id, db, ecfr_client):
    """
    Get document content for a descriptor and store it in the database.
    
    Args:
        descriptor: The AgencyTitleSearchDescriptor object
        agency_id: The ID of the agency
        db: The database session
        ecfr_client: The ECFRApiClient instance
        
    Returns:
        bool: True if content was added, False otherwise
    """
    logger = get_logger(__name__)
    
    # Get document content if hierarchy has title and chapter
    if descriptor.hierarchy and descriptor.hierarchy.get("title") and descriptor.hierarchy.get("chapter"):
        # Use the descriptor's date instead of today's date
        # First try ends_on, then starts_on, then fall back to today
        content_date = None
        
        if descriptor.ends_on:
            # Check if ends_on is already a string
            if isinstance(descriptor.ends_on, str):
                content_date = descriptor.ends_on
            else:
                # If it's a date object, format it
                content_date = descriptor.ends_on.strftime("%Y-%m-%d")
        elif descriptor.starts_on:
            # Check if starts_on is already a string
            if isinstance(descriptor.starts_on, str):
                content_date = descriptor.starts_on
            else:
                # If it's a date object, format it
                content_date = descriptor.starts_on.strftime("%Y-%m-%d")
        else:
            # If no dates are available, use today's date
            content_date = datetime.now().strftime("%Y-%m-%d")
        
        logger.debug(f"Using date {content_date} for document content retrieval")
        
        logger.trace(f"Fetching XML content for title={descriptor.hierarchy['title']}, chapter={descriptor.hierarchy.get('chapter')}")
        xml_content = ecfr_client.get_document_content(
            content_date,
            descriptor.hierarchy["title"],
            chapter=descriptor.hierarchy.get("chapter"),
            part=descriptor.hierarchy.get("part"),
            section=descriptor.hierarchy.get("section"),
            appendix=descriptor.hierarchy.get("appendix")
        )
        
        if xml_content:
            logger.trace(f"Received XML content of length {len(xml_content)}")
            # Check if we already have this content
            # Parse the content_date string to a date object if needed
            version_date = None
            if isinstance(content_date, str):
                try:
                    version_date = datetime.strptime(content_date, "%Y-%m-%d").date()
                except ValueError:
                    # If the date format is invalid, use today's date
                    logger.warning(f"Invalid date format: {content_date}, using today's date instead")
                    version_date = datetime.now().date()
            else:
                version_date = content_date
                
            logger.trace(f"Checking for existing content with descriptor_id={descriptor.id}, version_date={version_date}")
            existing_content = db.query(DocumentContent).filter(
                DocumentContent.descriptor_id == descriptor.id,
                DocumentContent.version_date == version_date
            ).first()
            
            if not existing_content:
                logger.trace(f"Processing XML content")
                # Process the XML content
                processed_text = XMLProcessor.extract_text_from_xml(xml_content)
                
                logger.trace(f"Creating new document content")
                # Create document content
                content = DocumentContent(
                    descriptor_id=descriptor.id,
                    agency_id=agency_id,
                    version_date=version_date,
                    raw_xml=xml_content,
                    processed_text=processed_text
                )
                db.add(content)
                db.flush()  # Flush to get the content ID
                
                # Create or get AgencyDocument record
                document_title = f"Title {descriptor.hierarchy['title']}"
                if descriptor.hierarchy.get('chapter'):
                    document_title += f", Chapter {descriptor.hierarchy['chapter']}"
                if descriptor.hierarchy.get('part'):
                    document_title += f", Part {descriptor.hierarchy['part']}"
                
                document_id_str = f"T{descriptor.hierarchy['title']}"
                if descriptor.hierarchy.get('chapter'):
                    document_id_str += f"C{descriptor.hierarchy['chapter']}"
                if descriptor.hierarchy.get('part'):
                    document_id_str += f"P{descriptor.hierarchy['part']}"
                
                # Check if document already exists
                existing_document = db.query(AgencyDocument).filter(
                    AgencyDocument.document_id == document_id_str,
                    AgencyDocument.agency_id == agency_id
                ).first()
                
                if not existing_document:
                    # Create new document
                    document = AgencyDocument(
                        title=document_title,
                        document_id=document_id_str,
                        agency_id=agency_id,
                        agency_metadata=descriptor.hierarchy,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    db.add(document)
                    db.flush()  # Flush to get the document ID
                    logger.trace(f"Created new AgencyDocument with ID {document.id}")
                else:
                    document = existing_document
                    document.updated_at = datetime.now()
                    logger.trace(f"Using existing AgencyDocument with ID {document.id}")
                
                # Compute and save metrics
                compute_xml_metrics(content, agency_id, db)
                
                logger.trace(f"Added new document content to session")
                results_added += 1
            else:
                logger.trace(f"Content already exists, skipping")
            return True
        else:
            logger.warning(f"Failed to retrieve XML content for descriptor {descriptor.id}")
            return False
    else:
        logger.trace(f"Descriptor doesn't have required hierarchy information, skipping content retrieval")
        return False

    """Save working proxies to a file"""
    # Create a client with proxies
    ecfr_client = ECFRApiClient(use_proxies=True)
    
    if ecfr_client.proxy_manager:
        ecfr_client.proxy_manager.save_proxies("proxies.txt")
        return {
            "message": f"Saved {len(ecfr_client.proxy_manager.working_proxies)} proxies to proxies.txt"
        }
    else:
        return {
            "message": "No proxy manager available"
        }

def compute_and_save_metrics(document_content, agency_id, document_id, db):
    """
    Compute metrics from document content and save them to the AgencyRegulationDocumentHistoricalMetrics table.
    
    Args:
        document_content: The DocumentContent object
        agency_id: The ID of the agency
        document_id: The ID of the document
        db: The database session
    
    Returns:
        The created AgencyRegulationDocumentHistoricalMetrics object
    """
    logger = get_logger(__name__)
    logger.info(f"Computing metrics for document {document_id}")
    
    # Get the processed text
    processed_text = document_content.processed_text
    
    if not processed_text:
        logger.warning(f"No processed text available for document {document_id}")
        return None
    
    # Compute metrics using XMLProcessor
    word_count = XMLProcessor.count_words(processed_text)
    paragraph_count = XMLProcessor.count_paragraphs(processed_text)
    sentence_count = XMLProcessor.count_sentences(processed_text)
    
    # Calculate average sentence length if possible
    average_sentence_length = None
    if sentence_count > 0:
        average_sentence_length = word_count / sentence_count
    
    # Create metrics record
    metrics = AgencyRegulationDocumentHistoricalMetrics(
        agency_id=agency_id,
        document_id=document_id,
        metrics_date=document_content.version_date,
        word_count=word_count,
        paragraph_count=paragraph_count,
        sentence_count=sentence_count,
        average_sentence_length=average_sentence_length,
        # Other fields are left as NULL for now
    )
    
    # Add to database
    db.add(metrics)
    logger.info(f"Saved metrics for document {document_id}: {word_count} words, {paragraph_count} paragraphs, {sentence_count} sentences")
    
    return metrics

def compute_xml_metrics(document_content, agency_id, db):
    """
    Compute XML metrics for a document content and save them to the database.
    
    Args:
        document_content: The DocumentContent object
        agency_id: The ID of the agency
        db: The database session
        
    Returns:
        The created AgencyRegulationDocumentHistoricalMetrics object or None if metrics could not be computed
    """
    logger = get_logger(__name__)
    
    if not document_content or not document_content.processed_text:
        logger.warning("Cannot compute metrics: document content is missing or has no processed text")
        return None
    
    # Create or get AgencyDocument record
    descriptor = db.query(AgencyTitleSearchDescriptor).filter(
        AgencyTitleSearchDescriptor.id == document_content.descriptor_id
    ).first()
    
    if not descriptor or not descriptor.hierarchy:
        logger.warning(f"Cannot compute metrics: descriptor {document_content.descriptor_id} not found or has no hierarchy")
        return None
    
    document_title = f"Title {descriptor.hierarchy['title']}"
    if descriptor.hierarchy.get('chapter'):
        document_title += f", Chapter {descriptor.hierarchy['chapter']}"
    if descriptor.hierarchy.get('part'):
        document_title += f", Part {descriptor.hierarchy['part']}"
    
    document_id_str = f"T{descriptor.hierarchy['title']}"
    if descriptor.hierarchy.get('chapter'):
        document_id_str += f"C{descriptor.hierarchy['chapter']}"
    if descriptor.hierarchy.get('part'):
        document_id_str += f"P{descriptor.hierarchy['part']}"
    
    # Check if document already exists
    existing_document = db.query(AgencyDocument).filter(
        AgencyDocument.document_id == document_id_str,
        AgencyDocument.agency_id == agency_id
    ).first()
    
    if not existing_document:
        # Create new document
        document = AgencyDocument(
            title=document_title,
            document_id=document_id_str,
            agency_id=agency_id,
            agency_metadata=descriptor.hierarchy,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(document)
        db.flush()  # Flush to get the document ID
        logger.trace(f"Created new AgencyDocument with ID {document.id}")
    else:
        document = existing_document
        document.updated_at = datetime.now()
        logger.trace(f"Using existing AgencyDocument with ID {document.id}")
    
    # Compute and save metrics
    return compute_and_save_metrics(document_content, agency_id, document.id, db)