import requests
import time
import random
import logging
import json
import os
from typing import List, Dict, Optional, Tuple, Any
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

class ProxyService:
    def __init__(self, proxy_list_path: str = "proxies.json", proxy_sources: List[str] = None):
        """
        Initialize the proxy service.
        
        Args:
            proxy_list_path: Path to the file where working proxies will be saved
            proxy_sources: List of URLs or file paths to fetch proxies from
        """
        self.proxy_list_path = proxy_list_path
        self.proxy_sources = proxy_sources or []
        self.all_proxies = []
        self.proxies = []
        
        # Load proxies from sources
        self._load_proxies_from_sources()
        
        # Load previously saved working proxies
        self._load_working_proxies()
        
        logging.info(f"Initialized ProxyService with {len(self.all_proxies)} total proxies and {len(self.proxies)} working proxies")
    
    def _load_proxies_from_sources(self):
        """Load proxies from configured sources"""
        # Implementation for loading from various sources would go here
        # For now, we'll assume self.all_proxies gets populated from somewhere
        pass
    
    def _load_working_proxies(self):
        """Load previously saved working proxies from file"""
        if os.path.exists(self.proxy_list_path):
            try:
                with open(self.proxy_list_path, 'r') as f:
                    data = json.load(f)
                    self.proxies = data.get('working_proxies', [])
                logging.info(f"Loaded {len(self.proxies)} working proxies from {self.proxy_list_path}")
            except Exception as e:
                logging.error(f"Error loading working proxies: {str(e)}")
    
    def _save_working_proxies(self):
        """Save working proxies to file for persistence"""
        try:
            with open(self.proxy_list_path, 'w') as f:
                json.dump({'working_proxies': self.proxies}, f)
            logging.info(f"Saved {len(self.proxies)} working proxies to {self.proxy_list_path}")
        except Exception as e:
            logging.error(f"Error saving working proxies: {str(e)}")
    
    def test_proxy(self, proxy: str) -> Tuple[bool, float]:
        """
        Test a single proxy and return whether it's working and its response time.
        
        Args:
            proxy: The proxy URL to test
            
        Returns:
            Tuple of (is_working, response_time_in_seconds)
        """
        start_time = time.time()
        try:
            response = requests.get(
                'https://www.ecfr.gov/api/search/v1/agencies', 
                proxies={'http': proxy, 'https': proxy},
                timeout=10
            )
            response_time = time.time() - start_time
            return response.status_code == 200, response_time
        except Exception as e:
            logging.warning(f"Proxy test failed for {proxy}: {str(e)}")
            return False, 0
    
    def test_proxies(self, proxies: List[str], max_workers: int = 10) -> List[str]:
        """
        Test multiple proxies concurrently and return the working ones.
        
        Args:
            proxies: List of proxy URLs to test
            max_workers: Maximum number of concurrent threads
            
        Returns:
            List of working proxy URLs
        """
        working_proxies = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all proxy tests to the thread pool
            future_to_proxy = {executor.submit(self.test_proxy, proxy): proxy for proxy in proxies}
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_proxy):
                proxy = future_to_proxy[future]
                try:
                    is_working, response_time = future.result()
                    if is_working:
                        logging.info(f"Proxy {proxy} is working (response time: {response_time:.2f}s)")
                        working_proxies.append(proxy)
                    else:
                        logging.info(f"Proxy {proxy} is not working")
                except Exception as e:
                    logging.error(f"Error testing proxy {proxy}: {str(e)}")
        
        return working_proxies
    
    def add_working_proxy(self, proxy: str):
        """Add a working proxy to our list and save to file"""
        if proxy not in self.proxies:
            self.proxies.append(proxy)
            self._save_working_proxies()
    
    def fetch_free(self, url: str, headers: Optional[Dict[str, str]] = None) -> Tuple[int, Any]:
        """
        Fetch a URL using a free proxy if available, or directly if no proxies are working.
        Tests proxies on-the-fly during actual requests.
        
        Args:
            url: The URL to fetch
            headers: Optional headers to include in the request
            
        Returns:
            Tuple of (status_code, response_content)
        """
        # If we have working proxies, try using one
        if self.proxies:
            # Try with a random proxy from our working list
            proxy = random.choice(self.proxies)
            try:
                response = requests.get(
                    url, 
                    headers=headers,
                    proxies={'http': proxy, 'https': proxy},
                    timeout=10
                )
                return response.status_code, response.json() if response.status_code == 200 else None
            except Exception as e:
                logging.error(f"Request with proxy {proxy} failed: {str(e)}")
                # Remove failed proxy from our list
                if proxy in self.proxies:
                    self.proxies.remove(proxy)
                    self._save_working_proxies()
        
        # If we have no working proxies or the selected one failed, try an untested proxy
        untested_proxies = [p for p in self.all_proxies if p not in self.proxies]
        if untested_proxies:
            proxy = random.choice(untested_proxies)
            try:
                start_time = time.time()
                response = requests.get(
                    url, 
                    headers=headers,
                    proxies={'http': proxy, 'https': proxy},
                    timeout=10
                )
                # If successful, add to working proxies
                if response.status_code == 200:
                    logging.info(f"Found new working proxy: {proxy} (response time: {time.time() - start_time:.2f}s)")
                    self.add_working_proxy(proxy)
                return response.status_code, response.json() if response.status_code == 200 else None
            except Exception as e:
                logging.warning(f"Untested proxy {proxy} failed: {str(e)}")
                # Continue to direct request
        
        # If all else fails, make a direct request
        logging.warning("No working proxies available, making direct request")
        try:
            response = requests.get(url, headers=headers)
            return response.status_code, response.json() if response.status_code == 200 else None
        except Exception as e:
            logging.error(f"Direct request failed: {str(e)}")
            return 500, None 