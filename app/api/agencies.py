from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import traceback
import sys
from fastapi.responses import JSONResponse

from app.database.connection import get_db
from app.models.agency import Agency
from app.services.ecfr_api import ECFRApiClient
from app.schemas.agency import AgencyResponse

router = APIRouter()
ecfr_client = ECFRApiClient()

@router.get("/", response_model=List[AgencyResponse], response_model_exclude_unset=True, response_model_exclude_none=True)
async def get_agencies(db: Session = Depends(get_db)):
    """
    Get all agencies from the database.
    """
    try:
        print("\n=== Starting get_agencies function ===")
        agencies = db.query(Agency).all()
        print(f"Retrieved {len(agencies)} agencies from database")
        
        # Return agencies as JSON
        return JSONResponse(content=[{
            "name": agency.name,
            "short_name": agency.short_name,
            "display_name": agency.display_name,
            "sortable_name": agency.sortable_name,
            "slug": agency.slug,
            "children": agency.children,
            "cfr_references": agency.cfr_references
        } for agency in agencies])
    
    except Exception as e:
        print(f"Error retrieving agencies: {str(e)}")
        traceback.print_exc(file=sys.stdout)
        raise HTTPException(status_code=500, detail=f"Error retrieving agencies: {str(e)}")

@router.post("/refresh", status_code=200)
async def refresh_agencies(db: Session = Depends(get_db)):
    """
    Fetch all agencies from the eCFR API and store them in the database.
    Returns a success message when complete.
    """
    print("\n=== Starting refresh_agencies function ===")
    try:
        print("Getting database session...")
        # DB session is automatically provided by the Depends(get_db)
        print(f"Database session obtained: {db}")
        
        print("\nInitializing eCFR API client...")
        # ecfr_client is already initialized at module level
        print(f"eCFR client: {ecfr_client}")
        
        print("\nFetching agencies from eCFR API...")
        agencies_data = ecfr_client.get_agencies()
        print(f"Received data with type: {type(agencies_data)}")
        print(f"Received {len(agencies_data) if agencies_data else 0} agencies from API")
        
        # Print first agency as sample, safely
        if agencies_data and len(agencies_data) > 0:
            print(f"Sample agency data: {agencies_data[0]}")
        else:
            print("No agency data received from API")
            return JSONResponse(content={"status": "error", "message": "No agency data received from API"})
        
        print("\nStoring agencies in database...")
        agencies_added = 0
        agencies_updated = 0
        
        for agency_data in agencies_data:
            print(f"\nProcessing agency: {agency_data.get('name', 'Unknown name')}")
            
            # Check if agency has a slug
            if 'slug' not in agency_data:
                print(f"Warning: Agency missing slug field, skipping: {agency_data}")
                continue
                
            # Check if agency already exists
            print(f"Checking if agency with slug '{agency_data['slug']}' exists...")
            existing_agency = db.query(Agency).filter(Agency.slug == agency_data["slug"]).first()
            
            if existing_agency:
                print(f"Agency exists, updating: {existing_agency}")
                # Update existing agency
                for key, value in agency_data.items():
                    setattr(existing_agency, key, value)
                agencies_updated += 1
            else:
                print(f"Agency doesn't exist, creating new record")
                # Create new agency
                new_agency = Agency.from_api_response(agency_data)
                db.add(new_agency)
                agencies_added += 1
        
        print(f"\nCommitting changes to database...")
        db.commit()
        print(f"Database commit successful")
        print(f"Added {agencies_added} new agencies, updated {agencies_updated} existing agencies")
        
        print("=== refresh_agencies function completed successfully ===\n")
        return JSONResponse(content={
            "status": "success", 
            "message": "Agencies refreshed successfully",
            "details": {
                "added": agencies_added,
                "updated": agencies_updated,
                "total": agencies_added + agencies_updated
            }
        })
    
    except Exception as e:
        print("\n!!! ERROR in refresh_agencies function !!!")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        print("Traceback:")
        traceback.print_exc(file=sys.stdout)
        
        # Rollback the database session
        print("Rolling back database transaction...")
        db.rollback()
        print("Rollback complete")
        
        print("=== refresh_agencies function failed ===\n")
        raise HTTPException(status_code=500, detail=f"Error refreshing agencies: {str(e)}")

@router.get("/{slug}", response_model=AgencyResponse)
async def get_agency_by_slug(slug: str, db: Session = Depends(get_db)):
    """
    Get a specific agency by its slug.
    """
    agency = db.query(Agency).filter(Agency.slug == slug).first()
    if not agency:
        raise HTTPException(status_code=404, detail=f"Agency with slug '{slug}' not found")
    
    # Return agency as JSON
    return JSONResponse(content={
        "name": agency.name,
        "short_name": agency.short_name,
        "display_name": agency.display_name,
        "sortable_name": agency.sortable_name,
        "slug": agency.slug,
        "children": agency.children,
        "cfr_references": agency.cfr_references
    }) 