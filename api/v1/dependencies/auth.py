"""
API Authentication Dependencies

Provides authentication middleware for API key validation.
"""

import os
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from typing import Optional

# API Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Verify API key from request header.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        Validated API key

    Raises:
        HTTPException: If API key is invalid or missing
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Please provide X-API-Key header."
        )

    # Get expected API key from environment
    expected_key = os.getenv("API_KEY")
    if not expected_key:
        # Fail closed outside explicit test mode.
        if os.getenv("TESTING", "false").lower() == "true":
            return api_key
        raise HTTPException(
            status_code=500,
            detail="API key not configured on server"
        )

    if api_key != expected_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    return api_key