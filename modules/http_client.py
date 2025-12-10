"""
Base HTTP Client for External APIs

Provides unified HTTP request handling with retry logic, rate limiting,
and error handling for all external data sources.
"""

import time
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from functools import wraps
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


class RateLimiter:
    """Thread-safe rate limiter for API requests."""
    
    def __init__(self, max_calls: int, period: float):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum number of calls allowed in the period
            period: Time period in seconds
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = []
        self.lock = Lock()
    
    def __call__(self, func):
        """Decorator to rate limit function calls."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self.lock:
                now = time.time()
                # Remove calls outside the current period
                self.calls = [call_time for call_time in self.calls if call_time > now - self.period]
                
                if len(self.calls) >= self.max_calls:
                    # Calculate wait time
                    sleep_time = self.period - (now - self.calls[0])
                    if sleep_time > 0:
                        logger.info(f"Rate limit reached. Sleeping for {sleep_time:.2f}s")
                        time.sleep(sleep_time)
                        # Clean up old calls after sleeping
                        now = time.time()
                        self.calls = [call_time for call_time in self.calls if call_time > now - self.period]
                
                self.calls.append(now)
            
            return func(*args, **kwargs)
        
        return wrapper


class BaseAPIClient:
    """
    Base class for all external API clients.
    
    Provides:
    - Automatic retry with exponential backoff
    - Rate limiting
    - Session management
    - Standardized error handling
    - Request/response logging
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        rate_limit: Optional[tuple] = None,  # (max_calls, period_seconds)
        timeout: int = 30,
    ):
        """
        Initialize API client.
        
        Args:
            base_url: Base URL for the API
            api_key: API key for authentication
            headers: Additional headers to include in requests
            max_retries: Maximum number of retries for failed requests
            backoff_factor: Backoff factor for retry delays
            rate_limit: Tuple of (max_calls, period_seconds) for rate limiting
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        
        # Create session with retry logic
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set headers
        self.session.headers.update({
            'User-Agent': 'Economic-Dashboard-API/2.0',
            'Accept': 'application/json',
        })
        
        if headers:
            self.session.headers.update(headers)
        
        # Rate limiter
        self.rate_limiter = None
        if rate_limit:
            max_calls, period = rate_limit
            self.rate_limiter = RateLimiter(max_calls, period)
    
    def _apply_rate_limit(self, func):
        """Apply rate limiting to a function if configured."""
        if self.rate_limiter:
            return self.rate_limiter(func)
        return func
    
    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint."""
        endpoint = endpoint.lstrip('/')
        return f"{self.base_url}/{endpoint}"
    
    def _add_auth(self, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> tuple:
        """
        Add authentication to request parameters or headers.
        Override this method in subclasses for custom auth.
        
        Returns:
            Tuple of (params, headers)
        """
        params = params or {}
        headers = headers or {}
        
        if self.api_key:
            # Default: add as query parameter
            params['api_key'] = self.api_key
        
        return params, headers
    
    def _log_request(self, method: str, url: str, **kwargs):
        """Log request details."""
        logger.debug(f"{method.upper()} {url}")
        if 'params' in kwargs and kwargs['params']:
            # Don't log sensitive params
            safe_params = {k: v for k, v in kwargs['params'].items() if 'api_key' not in k.lower()}
            if safe_params:
                logger.debug(f"Params: {safe_params}")
    
    def _log_response(self, response: requests.Response):
        """Log response details."""
        logger.debug(f"Response: {response.status_code} ({response.elapsed.total_seconds():.2f}s)")
    
    def _handle_error(self, response: requests.Response):
        """
        Handle HTTP errors with detailed logging.
        Override this in subclasses for API-specific error handling.
        """
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error: {e}")
            logger.error(f"Response body: {response.text[:500]}")
            raise
    
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> requests.Response:
        """
        Make a GET request.
        
        Args:
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            headers: Additional headers
            **kwargs: Additional arguments to pass to requests.get
            
        Returns:
            Response object
        """
        url = self._build_url(endpoint)
        params, headers = self._add_auth(params, headers)
        
        @self._apply_rate_limit
        def _make_request():
            self._log_request('GET', url, params=params)
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )
            self._log_response(response)
            self._handle_error(response)
            return response
        
        return _make_request()
    
    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> requests.Response:
        """
        Make a POST request.
        
        Args:
            endpoint: API endpoint (relative to base_url)
            data: Form data
            json: JSON data
            params: Query parameters
            headers: Additional headers
            **kwargs: Additional arguments to pass to requests.post
            
        Returns:
            Response object
        """
        url = self._build_url(endpoint)
        params, headers = self._add_auth(params, headers)
        
        @self._apply_rate_limit
        def _make_request():
            self._log_request('POST', url, params=params)
            response = self.session.post(
                url,
                data=data,
                json=json,
                params=params,
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )
            self._log_response(response)
            self._handle_error(response)
            return response
        
        return _make_request()
    
    def get_json(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a GET request and return JSON response."""
        response = self.get(endpoint, **kwargs)
        return response.json()
    
    def get_text(self, endpoint: str, **kwargs) -> str:
        """Make a GET request and return text response."""
        response = self.get(endpoint, **kwargs)
        return response.text
    
    def download_file(self, endpoint: str, output_path: str, **kwargs):
        """Download a file from the API."""
        response = self.get(endpoint, stream=True, **kwargs)
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Downloaded file to {output_path}")
    
    def close(self):
        """Close the session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class FREDClient(BaseAPIClient):
    """Client for FRED (Federal Reserve Economic Data) API."""
    
    def __init__(self, api_key: str):
        super().__init__(
            base_url='https://api.stlouisfed.org/fred',
            api_key=api_key,
            rate_limit=(120, 60),  # 120 calls per minute
        )
    
    def _add_auth(self, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> tuple:
        """Add FRED API key to parameters."""
        params = params or {}
        headers = headers or {}
        params['api_key'] = self.api_key
        params['file_type'] = 'json'
        return params, headers


class YahooFinanceClient(BaseAPIClient):
    """Client for Yahoo Finance (via yfinance library wrapper)."""
    
    def __init__(self):
        # Yahoo Finance doesn't require API key but has rate limits
        super().__init__(
            base_url='https://query1.finance.yahoo.com',
            rate_limit=(2000, 3600),  # Conservative: 2000 calls per hour
        )


class CBOEClient(BaseAPIClient):
    """Client for CBOE (Chicago Board Options Exchange) data."""
    
    def __init__(self):
        super().__init__(
            base_url='https://cdn.cboe.com',
            rate_limit=(60, 60),  # 60 calls per minute
        )


class ICIClient(BaseAPIClient):
    """Client for ICI (Investment Company Institute) data."""
    
    def __init__(self):
        super().__init__(
            base_url='https://www.ici.org',
            rate_limit=(30, 60),  # 30 calls per minute
        )


class NewsAPIClient(BaseAPIClient):
    """Client for News API."""
    
    def __init__(self, api_key: str):
        super().__init__(
            base_url='https://newsapi.org/v2',
            api_key=api_key,
            rate_limit=(100, 86400),  # 100 calls per day for free tier
        )
    
    def _add_auth(self, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> tuple:
        """Add News API key to headers."""
        params = params or {}
        headers = headers or {}
        headers['X-Api-Key'] = self.api_key
        return params, headers


# Factory function for creating clients
def create_client(source: str, api_key: Optional[str] = None) -> BaseAPIClient:
    """
    Factory function to create appropriate API client.
    
    Args:
        source: Data source name ('fred', 'yahoo', 'cboe', 'ici', 'news')
        api_key: API key if required
        
    Returns:
        Appropriate API client instance
    """
    clients = {
        'fred': FREDClient,
        'yahoo': YahooFinanceClient,
        'cboe': CBOEClient,
        'ici': ICIClient,
        'news': NewsAPIClient,
    }
    
    source = source.lower()
    if source not in clients:
        raise ValueError(f"Unknown data source: {source}. Available: {list(clients.keys())}")
    
    client_class = clients[source]
    
    # Check if API key is required
    if source in ['fred', 'news']:
        if not api_key:
            raise ValueError(f"{source.upper()} requires an API key")
        return client_class(api_key)
    else:
        return client_class()
