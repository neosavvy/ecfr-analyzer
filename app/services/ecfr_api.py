import requests
from typing import List, Dict, Any

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
    
    def get_agency_documents(self, agency_slug: str) -> List[Dict[str, Any]]:
        """Get all documents for a specific agency"""
        # This is a placeholder - you'll need to adjust based on the actual API
        url = f"{self.BASE_URL}/admin/v1/agencies/{agency_slug}/documents.json"
        response = self.session.get(url)
        response.raise_for_status()
        
        return response.json() 