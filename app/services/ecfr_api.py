import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from app.utils.logging import get_logger
import time
import random
import os

class ECFRApiClient:
    """Client for interacting with the eCFR API"""
    
    BASE_URL = "https://www.ecfr.gov/api"
    
    def __init__(self, use_proxies: bool = False, proxies: List[str] = None):
        self.logger = get_logger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            "accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        
        
        
    def _get(self, url: str, params: Dict = None, **kwargs) -> requests.Response:
        """Make a GET request"""
        
        return self.session.get(url, params=params, **kwargs)
    
    def get_agencies(self) -> List[Dict[str, Any]]:
        """Get all agencies from the eCFR API"""
        self.logger.debug("Fetching agencies from eCFR API")
        url = f"{self.BASE_URL}/admin/v1/agencies.json"
        response = self._get(url)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Debug the raw response
        self.logger.trace(f"Raw API response: {response.text[:200]}...")  # Print first 200 chars
        
        data = response.json()
        
        # Debug the parsed JSON structure
        self.logger.trace(f"Response keys: {data.keys() if isinstance(data, dict) else 'Not a dictionary'}")
        
        # Handle different response structures
        if isinstance(data, dict) and "data" in data:
            # If the agencies are in a 'data' field
            self.logger.debug(f"Found {len(data['data'])} agencies in 'data' field")
            return data["data"]
        elif isinstance(data, dict) and "agencies" in data:
            # If the agencies are in an 'agencies' field
            self.logger.debug(f"Found {len(data['agencies'])} agencies in 'agencies' field")
            return data["agencies"]
        elif isinstance(data, list):
            # If the response is already a list of agencies
            self.logger.debug(f"Found {len(data)} agencies in list")
            return data
        else:
            # If we can't determine the structure, print it for debugging
            self.logger.warning(f"Unexpected API response structure: {data}")
            # Return an empty list to avoid errors
            return []
    
    def search_agency_documents(self, agency_slug: str, page: int = 1, per_page: int = 20, last_modified_on_or_after: str = None, last_modified_before: str = None) -> Dict[str, Any]:
        """
        Search for documents related to an agency
        
        Args:
            agency_slug: The slug of the agency
            page: Page number to retrieve
            per_page: Number of results per page
            last_modified_on_or_after: Optional date string in YYYY-MM-DD format for filtering documents modified on or after this date
            last_modified_before: Optional date string in YYYY-MM-DD format for filtering documents modified before this date
        """
        self.logger.debug(f"Searching documents for agency '{agency_slug}' (page={page}, per_page={per_page})")
        url = f"{self.BASE_URL}/search/v1/results"
        params = {
            "agency_slugs[]": agency_slug,
            "per_page": per_page,
            "page": page,
            "order": "relevance",
            "paginate_by": "results"
        }
        
        # Add date range parameters if provided
        if last_modified_on_or_after:
            params["last_modified_on_or_after"] = last_modified_on_or_after
        if last_modified_before:
            params["last_modified_before"] = last_modified_before
        
        # Retry logic for rate limiting
        max_retries = 3
        retry_count = 0
        base_wait_time = 10  # seconds
        
        while retry_count <= max_retries:
            try:
                self.logger.trace(f"Request URL: {url}, params: {params}, attempt: {retry_count+1}")
                response = self._get(url, params=params)
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_count += 1
                    wait_time = base_wait_time * (1 + random.random())  # Add jitter
                    self.logger.warning(f"Rate limited (429). Waiting {wait_time:.2f} seconds before retry {retry_count}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                data = response.json()
                self.logger.debug(f"Found {len(data.get('results', []))} results")
                return data
                
            except Exception as e:
                retry_count += 1
                if retry_count <= max_retries:
                    wait_time = base_wait_time * retry_count * (1 + random.random())  # Exponential backoff with jitter
                    self.logger.warning(f"Error: {str(e)}. Retrying in {wait_time:.2f} seconds ({retry_count}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Failed after {max_retries} retries: {str(e)}")
                    return {"results": []}
        
        return {"results": []}  # Return empty results if all retries fail
    
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
        self.logger.debug(f"Fetching document content for date={date_str}, title={title}, params={kwargs}")
        url = f"{self.BASE_URL}/versioner/v1/full/{date_str}/title-{title}.xml"
        
        # Add any additional parameters
        params = {}
        for key, value in kwargs.items():
            if value:
                params[key] = value
        
        # Retry logic for rate limiting
        max_retries = 3
        retry_count = 0
        base_wait_time = 10  # seconds
        
        while retry_count <= max_retries:
            try:
                self.logger.trace(f"Request URL: {url}, params: {params}, attempt: {retry_count+1}")
                response = self._get(url, params=params)
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_count += 1
                    wait_time = base_wait_time * (1 + random.random())  # Add jitter
                    self.logger.warning(f"Rate limited (429). Waiting {wait_time:.2f} seconds before retry {retry_count}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                
                # Check for date-related errors
                if response.status_code == 400 and "past the title's most recent issue date" in response.text:
                    self.logger.warning(f"Date error: {response.text}")
                    
                    # Try to extract the most recent date from the error message
                    match = re.search(r"most recent issue date of (\d{4}-\d{2}-\d{2})", response.text)
                    if match:
                        most_recent_date = match.group(1)
                        self.logger.info(f"Retrying with most recent date: {most_recent_date}")
                        
                        # Retry with the most recent date
                        retry_url = f"{self.BASE_URL}/versioner/v1/full/{most_recent_date}/title-{title}.xml"
                        self.logger.trace(f"Retry URL: {retry_url}, params: {params}")
                        retry_response = self._get(retry_url, params=params)
                        
                        # Handle rate limiting for the retry request
                        if retry_response.status_code == 429:
                            retry_count += 1
                            wait_time = base_wait_time * (1 + random.random())
                            self.logger.warning(f"Rate limited (429) on date retry. Waiting {wait_time:.2f} seconds")
                            time.sleep(wait_time)
                            continue
                        
                        retry_response.raise_for_status()
                        self.logger.debug(f"Successfully retrieved content with retry (length: {len(retry_response.text)})")
                        return retry_response.text
                
                # Raise for other HTTP errors
                response.raise_for_status()
                self.logger.debug(f"Successfully retrieved content (length: {len(response.text)})")
                return response.text
                
            except Exception as e:
                retry_count += 1
                if retry_count <= max_retries:
                    wait_time = base_wait_time * retry_count * (1 + random.random())  # Exponential backoff with jitter
                    self.logger.warning(f"Error: {str(e)}. Retrying in {wait_time:.2f} seconds ({retry_count}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Failed after {max_retries} retries: {str(e)}")
                    return None
        
        return None  # Should not reach here, but just in case
    
    def get_agency_document_count(self, agency_slug: str, last_modified_on_or_after: str = None, last_modified_before: str = None) -> Dict[str, Any]:
        """
        Get the total count of documents for an agency
        
        Args:
            agency_slug: The slug of the agency
            last_modified_on_or_after: Optional date string in YYYY-MM-DD format for filtering documents modified on or after this date
            last_modified_before: Optional date string in YYYY-MM-DD format for filtering documents modified before this date
        """
        self.logger.debug(f"Fetching document count for agency '{agency_slug}'")
        url = f"{self.BASE_URL}/search/v1/count"
        params = {
            "agency_slugs[]": agency_slug
        }
        
        # Add date range parameters if provided
        if last_modified_on_or_after:
            params["last_modified_on_or_after"] = last_modified_on_or_after
        if last_modified_before:
            params["last_modified_before"] = last_modified_before
        
        self.logger.trace(f"Request URL: {url}, params: {params}")
        response = self._get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        self.logger.debug(f"Document count: {data.get('meta', {}).get('total_count', 0)}")
        return data 