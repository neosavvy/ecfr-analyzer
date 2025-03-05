import random
from typing import List, Optional, Dict
import requests
import time
from app.utils.logging import get_logger
import os

class ProxyManager:
    """Manages a pool of proxies and rotates between them"""
    
    def __init__(self, proxies: List[str] = None):
        """
        Initialize the proxy manager.
        
        Args:
            proxies: List of proxy URLs in format "http://user:pass@host:port" or "http://host:port"
        """
        self.logger = get_logger(__name__)
        self.proxies = proxies or []
        self.working_proxies = []
        self.failed_proxies = {}  # proxy -> (failure_count, last_failure_time)
        
        # If proxies are provided, test them
        if self.proxies:
            self.test_proxies()
    
    def add_proxy(self, proxy: str) -> None:
        """Add a proxy to the pool"""
        if proxy not in self.proxies:
            self.proxies.append(proxy)
            self.test_proxy(proxy)
    
    def test_proxy(self, proxy: str) -> bool:
        """Test if a proxy is working"""
        try:
            self.logger.debug(f"Testing proxy: {self.mask_proxy(proxy)}")
            response = requests.get(
                "https://www.ecfr.gov/api/admin/v1/agencies.json",
                proxies={"http": proxy, "https": proxy},
                timeout=10
            )
            if response.status_code == 200:
                self.logger.info(f"Proxy {self.mask_proxy(proxy)} is working")
                if proxy not in self.working_proxies:
                    self.working_proxies.append(proxy)
                if proxy in self.failed_proxies:
                    del self.failed_proxies[proxy]
                return True
            else:
                self.logger.warning(f"Proxy {self.mask_proxy(proxy)} returned status code {response.status_code}")
                self.mark_proxy_failed(proxy)
                return False
        except Exception as e:
            self.logger.warning(f"Proxy {self.mask_proxy(proxy)} failed: {str(e)}")
            self.mark_proxy_failed(proxy)
            return False
    
    def test_proxies(self) -> None:
        """Test all proxies in the pool"""
        self.logger.info(f"Testing {len(self.proxies)} proxies")
        self.working_proxies = []
        for proxy in self.proxies:
            self.test_proxy(proxy)
        self.logger.info(f"Found {len(self.working_proxies)} working proxies")
    
    def get_proxy(self) -> Optional[str]:
        """Get a random working proxy"""
        # Check if we should retry any failed proxies
        current_time = time.time()
        retry_candidates = []
        
        for proxy, (count, last_time) in list(self.failed_proxies.items()):
            # Retry after exponential backoff based on failure count
            backoff = min(60 * 60, 60 * (2 ** (count - 1)))  # Max 1 hour backoff
            if current_time - last_time > backoff:
                retry_candidates.append(proxy)
        
        # Test retry candidates
        for proxy in retry_candidates:
            if self.test_proxy(proxy):
                return proxy
        
        # Return a random working proxy
        if self.working_proxies:
            return random.choice(self.working_proxies)
        
        # If no working proxies, try to find one
        if self.proxies:
            for proxy in self.proxies:
                if self.test_proxy(proxy):
                    return proxy
        
        return None
    
    def mark_proxy_failed(self, proxy: str) -> None:
        """Mark a proxy as failed"""
        if proxy in self.working_proxies:
            self.working_proxies.remove(proxy)
        
        if proxy in self.failed_proxies:
            count, _ = self.failed_proxies[proxy]
            self.failed_proxies[proxy] = (count + 1, time.time())
        else:
            self.failed_proxies[proxy] = (1, time.time())
    
    def mask_proxy(self, proxy: str) -> str:
        """Mask sensitive parts of proxy URL for logging"""
        if '@' in proxy:
            # There's authentication info
            protocol, rest = proxy.split('://', 1)
            auth, host_port = rest.split('@', 1)
            return f"{protocol}://****:****@{host_port}"
        return proxy

    def save_proxies(self, filename: str = "proxies.txt") -> None:
        """Save working proxies to a file"""
        try:
            with open(filename, "w") as f:
                for proxy in self.working_proxies:
                    f.write(f"{proxy}\n")
            self.logger.info(f"Saved {len(self.working_proxies)} proxies to {filename}")
        except Exception as e:
            self.logger.error(f"Error saving proxies to {filename}: {str(e)}")

    def load_proxies(self, filename: str = "proxies.txt") -> None:
        """Load proxies from a file"""
        try:
            if not os.path.exists(filename):
                self.logger.warning(f"Proxy file {filename} does not exist")
                return
            
            with open(filename, "r") as f:
                loaded_proxies = [line.strip() for line in f if line.strip()]
        
            self.logger.info(f"Loaded {len(loaded_proxies)} proxies from {filename}")
        
            # Add the loaded proxies
            for proxy in loaded_proxies:
                self.add_proxy(proxy)
            
        except Exception as e:
            self.logger.error(f"Error loading proxies from {filename}: {str(e)}") 