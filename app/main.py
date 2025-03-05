from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.api.agencies import router as agencies_router
from app.database.connection import get_db
from app.models.agency import Agency
from app.models.search_descriptor import AgencyTitleSearchDescriptor
from app.models.document_content import DocumentContent
from app.services.ecfr_api import ECFRApiClient
from app.services.xml_processor import XMLProcessor
from app.models.agency_document_count import AgencyDocumentCount

app = FastAPI(title="eCFR Analyzer", description="API for analyzing the Electronic Code of Federal Regulations")

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
    # Get the agency
    agency = db.query(Agency).filter(Agency.slug == agency_slug).first()
    if not agency:
        raise HTTPException(status_code=404, detail=f"Agency with slug '{agency_slug}' not found")
    
    # Initialize API client
    ecfr_client = ECFRApiClient()
    
    # Get document count
    count_data = ecfr_client.get_agency_document_count(agency_slug)
    total_count = count_data.get("meta", {}).get("total_count", 0)
    
    # Check if we have an existing count record
    count_record = db.query(AgencyDocumentCount).filter(
        AgencyDocumentCount.agency_id == agency.id,
        AgencyDocumentCount.is_complete < 2  # Not complete
    ).order_by(AgencyDocumentCount.query_date.desc()).first()
    
    # Determine the starting page
    current_page = 0
    if reset:
        # Reset pagination
        if count_record:
            count_record.current_page = 0
            count_record.is_complete = 0
    elif start_page is not None:
        # Use the specified page
        current_page = start_page
        if count_record:
            count_record.current_page = start_page
    elif count_record:
        # Resume from last page
        current_page = count_record.current_page
    
    # Create a new count record if needed
    if not count_record or reset:
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
    
    # Calculate total pages
    total_pages = (total_count + per_page - 1) // per_page
    
    # Check if we're done
    if current_page >= total_pages:
        count_record.is_complete = 2  # Mark as complete
        db.commit()
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
            break
            
        # Process the current page
        search_results = ecfr_client.search_agency_documents(agency_slug, page=current_page + 1, per_page=per_page)
        
        # Process and store search results
        results_added = 0
        descriptors_added = 0
        
        if "results" in search_results:
            for result in search_results["results"]:
                # Create or update search descriptor
                existing_descriptor = None
                
                # Check if we can identify the descriptor by structure_index
                if "structure_index" in result:
                    existing_descriptor = db.query(AgencyTitleSearchDescriptor).filter(
                        AgencyTitleSearchDescriptor.agency_id == agency.id,
                        AgencyTitleSearchDescriptor.structure_index == result["structure_index"]
                    ).first()
                
                if existing_descriptor:
                    # Update existing descriptor
                    for key, value in result.items():
                        setattr(existing_descriptor, key, value)
                    descriptor = existing_descriptor
                else:
                    # Create new descriptor
                    descriptor = AgencyTitleSearchDescriptor.from_api_response(result, agency.id)
                    db.add(descriptor)
                    descriptors_added += 1
                
                db.flush()  # Flush to get the ID
                
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
                    
                    print(f"Using date {content_date} for document content retrieval")
                    
                    xml_content = ecfr_client.get_document_content(
                        content_date,
                        descriptor.hierarchy["title"],
                        chapter=descriptor.hierarchy.get("chapter"),
                        part=descriptor.hierarchy.get("part"),
                        section=descriptor.hierarchy.get("section"),
                        appendix=descriptor.hierarchy.get("appendix")
                    )
                    
                    if xml_content:
                        # Check if we already have this content
                        # Parse the content_date string to a date object if needed
                        version_date = None
                        if isinstance(content_date, str):
                            try:
                                version_date = datetime.strptime(content_date, "%Y-%m-%d").date()
                            except ValueError:
                                # If the date format is invalid, use today's date
                                version_date = datetime.now().date()
                        else:
                            version_date = content_date
                        
                        existing_content = db.query(DocumentContent).filter(
                            DocumentContent.descriptor_id == descriptor.id,
                            DocumentContent.version_date == version_date
                        ).first()
                        
                        if not existing_content:
                            # Process the XML content
                            processed_text = XMLProcessor.extract_text_from_xml(xml_content)
                            
                            # Create document content
                            content = DocumentContent(
                                descriptor_id=descriptor.id,
                                agency_id=agency.id,
                                version_date=version_date,
                                raw_xml=xml_content,
                                processed_text=processed_text
                            )
                            db.add(content)
                            results_added += 1
        
        # Update counters
        total_results_added += results_added
        total_descriptors_added += descriptors_added
        pages_processed += 1
        
        # Update the count record
        current_page += 1
        count_record.current_page = current_page
        
        # Commit changes for this page
        db.commit()
        
        print(f"Processed page {current_page} of {total_pages} for agency '{agency.name}'")
        
        # If not processing all pages, break after the first page
        if not process_all:
            break
    
    # Check if we've completed all pages
    if current_page >= total_pages:
        count_record.is_complete = 2  # Mark as complete
        db.commit()
    
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