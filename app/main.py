from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import os
import time
from typing import List
import requests
from bs4 import BeautifulSoup

from app.api.agencies import router as agencies_router
from app.database.connection import get_db, SessionLocal
from app.models.agency import Agency
from app.models.search_descriptor import AgencyTitleSearchDescriptor
from app.models.document_content import DocumentContent
from app.services.ecfr_api import ECFRApiClient
from app.services.xml_processor import XMLProcessor
from app.models.agency_document_count import AgencyDocumentCount
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
    """
    logger.info(f"Starting get_agency_documents for agency_slug={agency_slug}, start_page={start_page}, per_page={per_page}")
    
    # Get the agency
    agency = db.query(Agency).filter(Agency.slug == agency_slug).first()
    if not agency:
        logger.error(f"Agency with slug '{agency_slug}' not found")
        raise HTTPException(status_code=404, detail=f"Agency with slug '{agency_slug}' not found")
    
    logger.debug(f"Found agency: {agency.name} (ID: {agency.id})")
    
    # Initialize API client
    ecfr_client = ECFRApiClient()
    
    # Get document count
    logger.debug(f"Fetching document count for agency '{agency_slug}'")
    count_data = ecfr_client.get_agency_document_count(agency_slug)
    total_count = count_data.get("meta", {}).get("total_count", 0)
    logger.info(f"Agency '{agency.name}' has {total_count} documents")
    
    # Check if we have an existing count record
    count_record = db.query(AgencyDocumentCount).filter(
        AgencyDocumentCount.agency_id == agency.id,
        AgencyDocumentCount.is_complete < 2  # Not complete
    ).order_by(AgencyDocumentCount.query_date.desc()).first()
    
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
            is_complete=1  # Mark as in progress
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
        search_results = ecfr_client.search_agency_documents(agency_slug, page=current_page + 1, per_page=per_page)
        
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

@app.post("/api/agencies/{agency_slug}/process")
async def process_agency_documents(agency_slug: str, db: Session = Depends(get_db)):
    """Process documents for agency - compute metrics for all documents"""
    # TODO: Implement document processing
    return {"message": f"Processing documents for agency {agency_slug}"}

@app.get("/api/agencies/{agency_slug}/documents/status")
async def get_agency_documents_status(agency_slug: str, db: Session = Depends(get_db)):
    """Get the status of document retrieval for an agency"""
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
            "message": f"No document retrieval has been started for agency '{agency.name}'",
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
        "message": f"Document retrieval for agency '{agency.name}' is {status}",
        "status": status,
        "total_count": count_record.total_count,
        "total_pages": total_pages,
        "current_page": count_record.current_page,
        "progress_percent": round(progress_percent, 2),
        "last_updated": count_record.query_date.isoformat()
    }

@app.post("/api/agencies/{agency_slug}/documents/fetch-all")
async def fetch_all_agency_documents(
    agency_slug: str,
    background_tasks: BackgroundTasks,
    per_page: int = 20,
    reset: bool = False,
    concurrent: bool = False,
    max_workers: int = 5,
    db: Session = Depends(get_db)
):
    """
    Fetch all documents for an agency in the background.
    
    Args:
        agency_slug: The slug of the agency
        per_page: Number of results per page
        reset: If True, will reset pagination and start from page 0
        concurrent: If True, will use concurrent processing
        max_workers: Maximum number of concurrent workers (only used if concurrent=True)
    """
    # Get the agency
    agency = db.query(Agency).filter(Agency.slug == agency_slug).first()
    if not agency:
        raise HTTPException(status_code=404, detail=f"Agency with slug '{agency_slug}' not found")
    
    # Initialize API client
    ecfr_client = ECFRApiClient()
    
    # Get document count
    count_data = ecfr_client.get_agency_document_count(agency_slug)
    total_count = count_data.get("meta", {}).get("total_count", 0)
    
    # Calculate total pages
    total_pages = (total_count + per_page - 1) // per_page
    
    # Reset the count record if requested
    if reset:
        count_record = db.query(AgencyDocumentCount).filter(
            AgencyDocumentCount.agency_id == agency.id
        ).order_by(AgencyDocumentCount.query_date.desc()).first()
        
        if count_record:
            count_record.current_page = 0
            count_record.is_complete = 0
            db.commit()
        
    # Create a new count record if needed
    count_record = db.query(AgencyDocumentCount).filter(
        AgencyDocumentCount.agency_id == agency.id
    ).order_by(AgencyDocumentCount.query_date.desc()).first()
    
    if not count_record:
        count_record = AgencyDocumentCount(
            agency_id=agency.id,
            reference_date=datetime.now().date(),
            total_count=total_count,
            current_page=0,
            per_page=per_page,
            is_complete=1  # Mark as in progress
        )
        db.add(count_record)
        db.commit()
    
    # Add the background task
    if concurrent:
        # Create a direct function call that doesn't depend on FastAPI context
        background_tasks.add_task(
            process_agency_documents_concurrent,
            agency_slug=agency_slug,
            agency_id=agency.id,
            total_pages=total_pages,
            per_page=per_page,
            max_workers=max_workers
        )
    else:
        background_tasks.add_task(
            process_agency_documents_sequential,
            agency_slug=agency_slug,
            agency_id=agency.id,
            total_pages=total_pages,
            per_page=per_page
        )
    
    return {
        "message": f"Started fetching all documents for agency '{agency.name}'",
        "total_count": total_count,
        "total_pages": total_pages,
        "processing_mode": "concurrent" if concurrent else "sequential",
        "status": "started"
    }

# Completely rewritten sequential processing function
def process_agency_documents_sequential(agency_slug: str, agency_id: int, total_pages: int, per_page: int):
    """Process all agency documents sequentially"""
    logger = get_logger("sequential_processor")
    logger.info(f"Starting sequential processing for agency '{agency_slug}' with {total_pages} pages")
    
    # Create a new database session
    db = SessionLocal()
    
    try:
        # Get the count record
        count_record = db.query(AgencyDocumentCount).filter(
            AgencyDocumentCount.agency_id == agency_id
        ).order_by(AgencyDocumentCount.query_date.desc()).first()
        
        if not count_record:
            logger.error(f"No count record found for agency {agency_id}")
            return
        
        # Set as in progress
        count_record.is_complete = 1
        db.commit()
        
        # Initialize API client with proxies
        ecfr_client = ECFRApiClient(use_proxies=True)
        
        # Start from the current page
        current_page = count_record.current_page
        
        # Process each page
        while current_page < total_pages:
            logger.info(f"Processing page {current_page + 1} of {total_pages}")
            
            # Get search results for this page
            search_results = ecfr_client.search_agency_documents(
                agency_slug, 
                page=current_page + 1, 
                per_page=per_page
            )
            
            # Process results
            results_added = 0
            descriptors_added = 0
            
            if "results" in search_results:
                for result in search_results["results"]:
                    # Process each result directly
                    descriptor = process_search_result(result, agency_id, db, ecfr_client)
                    if descriptor:
                        descriptors_added += 1
                        
                        # Get document content
                        content_added = get_and_store_document_content(descriptor, agency_id, db, ecfr_client)
                        if content_added:
                            results_added += 1
            
            # Update progress
            current_page += 1
            count_record.current_page = current_page
            db.commit()
            
            logger.info(f"Completed page {current_page} of {total_pages}. Added {descriptors_added} descriptors and {results_added} documents.")
        
        # Mark as complete
        count_record.is_complete = 2
        db.commit()
        logger.info(f"Completed all {total_pages} pages for agency '{agency_slug}'")
        
    except Exception as e:
        logger.error(f"Error in sequential processing: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        db.close()

# Completely rewritten concurrent processing function
def process_agency_documents_concurrent(agency_slug: str, agency_id: int, total_pages: int, per_page: int, max_workers: int):
    """Process all agency documents concurrently"""
    logger = get_logger("concurrent_processor")
    logger.info(f"Starting concurrent processing for agency '{agency_slug}' with {total_pages} pages using {max_workers} workers")
    
    # Create a new database session for tracking progress
    db = SessionLocal()
    
    try:
        # Get the count record
        count_record = db.query(AgencyDocumentCount).filter(
            AgencyDocumentCount.agency_id == agency_id
        ).order_by(AgencyDocumentCount.query_date.desc()).first()
        
        if not count_record:
            logger.error(f"No count record found for agency {agency_id}")
            return
        
        # Set as in progress
        count_record.is_complete = 1
        db.commit()
        
        # Start from the current page
        start_page = count_record.current_page
        
        # Create a list of pages to process
        pages_to_process = list(range(start_page, total_pages))
        logger.info(f"Will process {len(pages_to_process)} pages from {start_page} to {total_pages-1}")
        
        # Create a thread-safe counter for progress tracking
        progress_lock = Lock()
        completed_pages = 0
        
        # Function to process a single page
        def process_page(page_num):
            nonlocal completed_pages
            thread_logger = get_logger(f"concurrent_processor.thread.{page_num}")
            thread_logger.info(f"Starting processing for page {page_num + 1}")
            
            # Create a new database session for this thread
            thread_db = SessionLocal()
            
            try:
                # Initialize API client with proxies
                thread_ecfr_client = ECFRApiClient(use_proxies=True)
                
                # Get search results for this page
                search_results = thread_ecfr_client.search_agency_documents(
                    agency_slug, 
                    page=page_num + 1, 
                    per_page=per_page
                )
                
                # Process results
                results_added = 0
                descriptors_added = 0
                
                if "results" in search_results:
                    for result in search_results["results"]:
                        # Process each result directly
                        descriptor = process_search_result(result, agency_id, thread_db, thread_ecfr_client)
                        if descriptor:
                            descriptors_added += 1
                            
                            # Get document content
                            content_added = get_and_store_document_content(descriptor, agency_id, thread_db, thread_ecfr_client)
                            if content_added:
                                results_added += 1
                
                # Commit changes for this page
                thread_db.commit()
                
                # Update progress
                with progress_lock:
                    completed_pages += 1
                    thread_logger.info(f"Processed page {page_num + 1} of {total_pages}. Added {descriptors_added} descriptors and {results_added} documents. ({completed_pages}/{len(pages_to_process)} complete)")
                
            except Exception as e:
                thread_logger.error(f"Error processing page {page_num + 1}: {str(e)}")
                import traceback
                thread_logger.error(traceback.format_exc())
                thread_db.rollback()
            
            finally:
                thread_db.close()
        
        # Process pages using thread pool
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_page, page) for page in pages_to_process]
            
            # Wait for all futures to complete
            for future in futures:
                future.result()
        
        # Update the count record to mark as complete
        count_record.current_page = total_pages
        count_record.is_complete = 2
        db.commit()
        
        logger.info(f"Completed concurrent processing for agency '{agency_slug}'")
    
    except Exception as e:
        logger.error(f"Error in concurrent processing: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        db.close()

# Helper function to process a single search result
def process_search_result(result, agency_id, db, ecfr_client):
    """Process a single search result and return the descriptor"""
    logger = get_logger("result_processor")
    
    try:
        # Check if we can identify the descriptor by structure_index
        existing_descriptor = None
        if "structure_index" in result:
            existing_descriptor = db.query(AgencyTitleSearchDescriptor).filter(
                AgencyTitleSearchDescriptor.agency_id == agency_id,
                AgencyTitleSearchDescriptor.structure_index == result["structure_index"]
            ).first()
        
        if existing_descriptor:
            # Check if processing_status attribute exists (for backward compatibility)
            if hasattr(existing_descriptor, 'processing_status') and existing_descriptor.processing_status == 2:
                logger.debug(f"Descriptor {existing_descriptor.id} already processed, skipping")
                return existing_descriptor
                
            # Update existing descriptor
            for key, value in result.items():
                if hasattr(existing_descriptor, key):
                    setattr(existing_descriptor, key, value)
            descriptor = existing_descriptor
        else:
            # Create new descriptor
            descriptor = AgencyTitleSearchDescriptor.from_api_response(result, agency_id)
            db.add(descriptor)
        
        # Set processing status if the attribute exists
        if hasattr(descriptor, 'processing_status'):
            descriptor.processing_status = 1
        
        # Flush to get the ID
        db.flush()
        return descriptor
    
    except Exception as e:
        logger.error(f"Error processing search result: {str(e)}")
        db.rollback()
        return None

# Helper function to get and store document content
def get_and_store_document_content(descriptor, agency_id, db, ecfr_client):
    """Get and store document content for a descriptor"""
    logger = get_logger("content_processor")
    
    try:
        # Check if hierarchy has title and chapter
        if not (descriptor.hierarchy and descriptor.hierarchy.get("title") and descriptor.hierarchy.get("chapter")):
            if hasattr(descriptor, 'processing_status'):
                descriptor.processing_status = 2  # Mark as completed even though we can't process it
            return False
        
        # Determine content date
        content_date = None
        if descriptor.ends_on:
            if isinstance(descriptor.ends_on, str):
                content_date = descriptor.ends_on
            else:
                content_date = descriptor.ends_on.strftime("%Y-%m-%d")
        elif descriptor.starts_on:
            if isinstance(descriptor.starts_on, str):
                content_date = descriptor.starts_on
            else:
                content_date = descriptor.starts_on.strftime("%Y-%m-%d")
        else:
            content_date = datetime.now().strftime("%Y-%m-%d")
        
        # Get document content
        xml_content = ecfr_client.get_document_content(
            content_date,
            descriptor.hierarchy["title"],
            chapter=descriptor.hierarchy.get("chapter"),
            part=descriptor.hierarchy.get("part"),
            section=descriptor.hierarchy.get("section"),
            appendix=descriptor.hierarchy.get("appendix")
        )
        
        if not xml_content:
            if hasattr(descriptor, 'processing_status'):
                descriptor.processing_status = 3  # Mark as error
            return False
        
        # Parse content date
        version_date = None
        if isinstance(content_date, str):
            try:
                version_date = datetime.strptime(content_date, "%Y-%m-%d").date()
            except ValueError:
                version_date = datetime.now().date()
        else:
            version_date = content_date
        
        # Check if content already exists
        existing_content = db.query(DocumentContent).filter(
            DocumentContent.descriptor_id == descriptor.id,
            DocumentContent.version_date == version_date
        ).first()
        
        if existing_content:
            if hasattr(descriptor, 'processing_status'):
                descriptor.processing_status = 2  # Mark as completed
            return False
        
        # Process XML content
        processed_text = XMLProcessor.extract_text_from_xml(xml_content)
        
        # Create document content
        content = DocumentContent(
            descriptor_id=descriptor.id,
            agency_id=agency_id,
            version_date=version_date,
            raw_xml=xml_content,
            processed_text=processed_text
        )
        db.add(content)
        
        # Mark descriptor as completed
        if hasattr(descriptor, 'processing_status'):
            descriptor.processing_status = 2
        
        return True
    
    except Exception as e:
        logger.error(f"Error getting/storing document content: {str(e)}")
        if hasattr(descriptor, 'processing_status'):
            descriptor.processing_status = 3  # Mark as error
        return False

@app.get("/api/agencies/{agency_slug}/documents/fetch-status")
async def get_fetch_status(agency_slug: str, db: Session = Depends(get_db)):
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

@app.post("/api/agencies/{agency_slug}/documents/retry-failed")
async def retry_failed_documents(
    agency_slug: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Retry processing failed documents"""
    # Get the agency
    agency = db.query(Agency).filter(Agency.slug == agency_slug).first()
    if not agency:
        raise HTTPException(status_code=404, detail=f"Agency with slug '{agency_slug}' not found")
    
    try:
        # Count failed descriptors
        failed_count = db.query(AgencyTitleSearchDescriptor).filter(
            AgencyTitleSearchDescriptor.agency_id == agency.id,
            AgencyTitleSearchDescriptor.processing_status == 3  # error
        ).count()
        
        # Reset status to not processed
        db.query(AgencyTitleSearchDescriptor).filter(
            AgencyTitleSearchDescriptor.agency_id == agency.id,
            AgencyTitleSearchDescriptor.processing_status == 3  # error
        ).update({"processing_status": 0})
        
        db.commit()
    except Exception as e:
        # If the column doesn't exist yet, handle gracefully
        logger.warning(f"Could not access processing_status column: {str(e)}")
        failed_count = 0
    
    # Add background task to process failed documents
    background_tasks.add_task(
        process_failed_documents,
        agency_slug=agency_slug,
        agency_id=agency.id
    )
    
    return {
        "message": f"Started retry of {failed_count} failed documents for agency '{agency.name}'",
        "failed_count": failed_count,
        "status": "started"
    }

def process_failed_documents(agency_slug: str, agency_id: int):
    """Process failed documents"""
    logger = get_logger("failed_processor")
    logger.info(f"Starting to process failed documents for agency '{agency_slug}'")
    
    # Create a new database session
    db = SessionLocal()
    
    try:
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
    
    except Exception as e:
        logger.error(f"Error processing failed documents: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        db.close()

@app.post("/api/proxies")
async def add_proxies(proxies: List[str], db: Session = Depends(get_db)):
    """Add proxies to the proxy pool"""
    # Initialize API client with proxies
    ecfr_client = ECFRApiClient(use_proxies=True, proxies=proxies)
    
    # Test the proxies
    working_proxies = []
    for proxy in proxies:
        if ecfr_client.proxy_manager.test_proxy(proxy):
            working_proxies.append(proxy)
    
    return {
        "message": f"Added {len(working_proxies)} working proxies out of {len(proxies)} provided",
        "working_proxies": len(working_proxies),
        "total_proxies": len(proxies)
    }

@app.post("/api/proxies/fetch-free")
async def fetch_free_proxies(db: Session = Depends(get_db)):
    """Fetch and add free proxies from public proxy lists"""
    proxies = []
    
    # Try to fetch from free-proxy-list.net
    try:
        logger.info("Fetching proxies from free-proxy-list.net")
        response = requests.get("https://free-proxy-list.net/", 
                               headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the proxy table
        table = soup.find('table', {'id': 'proxylisttable'})
        if table:
            # Extract proxies
            for row in table.find('tbody').find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 7:
                    ip = cells[0].text.strip()
                    port = cells[1].text.strip()
                    https = cells[6].text.strip()
                    
                    if https == 'yes':
                        proxy = f"https://{ip}:{port}"
                        proxies.append(proxy)
                    else:
                        proxy = f"http://{ip}:{port}"
                        proxies.append(proxy)
            
            logger.info(f"Found {len(proxies)} proxies from free-proxy-list.net")
        else:
            logger.warning("Could not find proxy table on free-proxy-list.net")
    
    except Exception as e:
        logger.error(f"Error fetching proxies from free-proxy-list.net: {str(e)}")
    
    # Try to fetch from proxyscrape.com
    try:
        logger.info("Fetching proxies from proxyscrape.com")
        response = requests.get("https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all")
        proxy_list = response.text.strip().split('\r\n')
        
        for proxy in proxy_list:
            if proxy:
                proxies.append(f"http://{proxy}")
        
        logger.info(f"Found {len(proxy_list)} proxies from proxyscrape.com")
    
    except Exception as e:
        logger.error(f"Error fetching proxies from proxyscrape.com: {str(e)}")
    
    # # Initialize API client with proxies
    # ecfr_client = ECFRApiClient(use_proxies=True, proxies=proxies)
    
    # Test the proxies
    working_proxies = []
    for proxy in proxies:
        # if ecfr_client.proxy_manager.test_proxy(proxy):
        working_proxies.append(proxy)
    
    return {
        "message": f"Added {len(working_proxies)} working proxies out of {len(proxies)} found",
        "working_proxies": len(working_proxies),
        "total_proxies": len(proxies)
    }

@app.post("/api/proxies/save")
async def save_proxies():
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