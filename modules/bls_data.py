"""
BLS (Bureau of Labor Statistics) Data Loader

Fetches economic data from the BLS API:
https://www.bls.gov/developers/

BLS provides:
- Employment and unemployment data
- Consumer Price Index (CPI)
- Producer Price Index (PPI)
- Wages and benefits
- Productivity statistics
- Granular US labor market data
"""

import pandas as pd
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import os
from modules.http_client import BLSClient

logger = logging.getLogger(__name__)


# Popular BLS series IDs
BLS_SERIES = {
    'LNS14000000': 'Unemployment Rate',
    'CES0000000001': 'Total Nonfarm Employment',
    'CUUR0000SA0': 'CPI-U (All Items)',
    'CUSR0000SA0': 'CPI-W (All Items)',
    'WPUFD49207': 'PPI (Final Demand)',
    'CES0500000003': 'Average Hourly Earnings - Private Sector',
    'LNS12300000': 'Labor Force Participation Rate',
    'CES0000000007': 'Average Weekly Hours - Private Sector',
}


def fetch_bls_series(
    series_ids: List[str],
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    api_key: Optional[str] = None
) -> pd.DataFrame:
    """
    Fetch BLS data for specified series.
    
    Args:
        series_ids: List of BLS series IDs
        start_year: Start year (default: 10 years ago)
        end_year: End year (default: current year)
        api_key: Optional BLS API key for higher rate limits
        
    Returns:
        DataFrame with BLS data
    """
    logger.info(f"Fetching {len(series_ids)} BLS series")
    
    # Get API key from environment if not provided
    if api_key is None:
        api_key = os.getenv('BLS_API_KEY')
    
    client = BLSClient(api_key=api_key)
    
    # Set default date range
    if start_year is None:
        start_year = datetime.now().year - 10
    if end_year is None:
        end_year = datetime.now().year
    
    try:
        # BLS API requires POST with JSON body
        payload = {
            'seriesid': series_ids,
            'startyear': str(start_year),
            'endyear': str(end_year),
        }
        
        # Add API key to payload if available
        if api_key:
            payload['registrationkey'] = api_key
        
        # BLS API endpoint
        endpoint = '/timeseries/data/'
        
        response = client.post(
            endpoint,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        data = response.json()
        
        if data.get('status') != 'REQUEST_SUCCEEDED':
            logger.error(f"BLS API error: {data.get('message', 'Unknown error')}")
            return pd.DataFrame()
        
        # Parse series data
        records = []
        
        for series in data.get('Results', {}).get('series', []):
            series_id = series.get('seriesID', '')
            series_name = BLS_SERIES.get(series_id, series_id)
            
            for item in series.get('data', []):
                # BLS returns data in reverse chronological order
                year = int(item.get('year', 0))
                period = item.get('period', '')
                value = item.get('value', '')
                
                if value and value != '':
                    # Parse period (M01-M12 for monthly, Q01-Q04 for quarterly, A01 for annual)
                    if period.startswith('M'):
                        month = int(period[1:])
                        date = f"{year}-{month:02d}-01"
                    elif period.startswith('Q'):
                        quarter = int(period[1:])
                        month = (quarter - 1) * 3 + 1
                        date = f"{year}-{month:02d}-01"
                    elif period == 'A01':
                        date = f"{year}-12-31"
                    else:
                        continue
                    
                    records.append({
                        'series_id': series_id,
                        'series_name': series_name,
                        'year': year,
                        'period': period,
                        'value': float(value),
                        'date': date,
                    })
        
        df = pd.DataFrame(records)
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
        
        logger.info(f"Fetched {len(df)} BLS records")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching BLS data: {e}")
        raise
    finally:
        client.close()


def fetch_bls_unemployment() -> pd.DataFrame:
    """
    Fetch unemployment rate data from BLS.
    
    Returns:
        DataFrame with unemployment rate
    """
    logger.info("Fetching BLS unemployment rate")
    
    return fetch_bls_series(
        series_ids=['LNS14000000'],  # Unemployment Rate
        start_year=datetime.now().year - 10
    )


def fetch_bls_cpi() -> pd.DataFrame:
    """
    Fetch Consumer Price Index data from BLS.
    
    Returns:
        DataFrame with CPI data
    """
    logger.info("Fetching BLS CPI data")
    
    return fetch_bls_series(
        series_ids=['CUUR0000SA0', 'CUSR0000SA0'],  # CPI-U and CPI-W
        start_year=datetime.now().year - 10
    )


def fetch_bls_employment() -> pd.DataFrame:
    """
    Fetch employment data from BLS.
    
    Returns:
        DataFrame with employment statistics
    """
    logger.info("Fetching BLS employment data")
    
    return fetch_bls_series(
        series_ids=[
            'CES0000000001',  # Total Nonfarm Employment
            'LNS12300000',    # Labor Force Participation Rate
            'CES0000000007',  # Average Weekly Hours
        ],
        start_year=datetime.now().year - 10
    )


def fetch_bls_wages() -> pd.DataFrame:
    """
    Fetch wage data from BLS.
    
    Returns:
        DataFrame with wage statistics
    """
    logger.info("Fetching BLS wage data")
    
    return fetch_bls_series(
        series_ids=['CES0500000003'],  # Average Hourly Earnings
        start_year=datetime.now().year - 10
    )


def refresh_bls_data(
    series_ids: Optional[List[str]] = None,
    api_key: Optional[str] = None
) -> int:
    """
    Refresh BLS data in the database.
    
    This is the main entry point called by schedulers.
    
    Args:
        series_ids: List of BLS series IDs. If None, uses popular series
        api_key: Optional BLS API key
        
    Returns:
        Number of records inserted
    """
    from modules.database.queries import insert_generic_data
    
    # Default to popular series
    if series_ids is None:
        series_ids = list(BLS_SERIES.keys())
    
    logger.info(f"Refreshing BLS data for {len(series_ids)} series")
    
    df = fetch_bls_series(
        series_ids=series_ids,
        start_year=datetime.now().year - 10,
        api_key=api_key
    )
    
    if not df.empty:
        records_inserted = insert_generic_data(df, 'bls_data')
        logger.info(f"Inserted {records_inserted} BLS records")
        return records_inserted
    
    return 0
