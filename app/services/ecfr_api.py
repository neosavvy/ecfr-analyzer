import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

class ECFRApiClient:
    """Client for interacting with the eCFR API"""
    
    BASE_URL = "https://www.ecfr.gov/api"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "accept": "application/json"
        })
    
    def get_agencies(self) -> List[Dict[str, Any]]:
        """Get all agencies from the eCFR API"""
        url = f"{self.BASE_URL}/admin/v1/agencies.json"
        response = self.session.get(url)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Debug the raw response
        print(f"Raw API response: {response.text[:200]}...")  # Print first 200 chars
        
        data = response.json()
        
        # Debug the parsed JSON structure
        print(f"Response keys: {data.keys() if isinstance(data, dict) else 'Not a dictionary'}")
        
        # Handle different response structures
        if isinstance(data, dict) and "data" in data:
            # If the agencies are in a 'data' field
            return data["data"]
        elif isinstance(data, dict) and "agencies" in data:
            # If the agencies are in an 'agencies' field
            return data["agencies"]
        elif isinstance(data, list):
            # If the response is already a list of agencies
            return data
        else:
            # If we can't determine the structure, print it for debugging
            print(f"Unexpected API response structure: {data}")
            # Return an empty list to avoid errors
            return []
    
    def search_agency_documents(self, agency_slug: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Search for documents related to an agency"""
        url = f"{self.BASE_URL}/search/v1/results"
        params = {
            "agency_slugs[]": agency_slug,
            "per_page": per_page,
            "page": page,
            "order": "relevance",
            "paginate_by": "results"
        }
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def get_document_content(self, date_str: str, title: str, **kwargs) -> Optional[str]:
        """
        Get the XML content of a document for a specific date.
        
        Args:
            date_str: Date in YYYY-MM-DD format
            title: Title number (e.g., "48")
            **kwargs: Additional parameters like chapter, part, etc.
        
        Returns:
            XML content as string or None if not found
        """
        url = f"{self.BASE_URL}/versioner/v1/full/{date_str}/title-{title}.xml"
        
        # Add any additional parameters
        params = {}
        for key, value in kwargs.items():
            if value:
                params[key] = value
        
        try:
            response = self.session.get(url, params=params)
            
            # Check for date-related errors
            if response.status_code == 400 and "past the title's most recent issue date" in response.text:
                print(f"Date error: {response.text}")
                
                # Try to extract the most recent date from the error message
                match = re.search(r"most recent issue date of (\d{4}-\d{2}-\d{2})", response.text)
                if match:
                    most_recent_date = match.group(1)
                    print(f"Retrying with most recent date: {most_recent_date}")
                    
                    # Retry with the most recent date
                    retry_url = f"{self.BASE_URL}/versioner/v1/full/{most_recent_date}/title-{title}.xml"
                    retry_response = self.session.get(retry_url, params=params)
                    retry_response.raise_for_status()
                    return retry_response.text
            
            # Raise for other HTTP errors
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching document content: {str(e)}")
            return None
    
    def get_agency_document_count(self, agency_slug: str) -> Dict[str, Any]:
        """Get the total count of documents for an agency"""
        url = f"{self.BASE_URL}/search/v1/count"
        params = {
            "agency_slugs[]": agency_slug
        }
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        
        return response.json() 