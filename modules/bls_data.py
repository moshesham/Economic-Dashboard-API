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
import os
from modules.http_client import BLSClient

logger = logging.getLogger(__name__)

# Expanded BLS series categorized by indicator type
BLS_SERIES_CATEGORIES = {
    "Employment & Slack": {
        'LNS14000000': 'Unemployment Rate (U-3)',
        'LNS13327709': 'Broad Underemployment Rate (U-6)',
        'CES0000000001': 'Total Nonfarm Employment',
        'LNS12300000': 'Labor Force Participation Rate (Aggregate)',
        'LNS11300060': 'Labor Force Participation Rate (Prime-Age 25-54)',
    },
    "Labor Market Churn (JOLTS)": {
        'JTS000000000000000JOL': 'JOLTS Total Job Openings (SA, Thousands)',
        'JTS000000000000000QUR': 'JOLTS Quits Rate (SA)',
    },
    "Inflation & Prices": {
        'CUUR0000SA0': 'CPI-U (All Items, NSA)',
        'CUSR0000SA0L1E': 'Core CPI-U (Less Food & Energy, SA)',
        'WPUFD49207': 'PPI (Final Demand)',
    },
    "Wages & Productivity": {
        'CES0500000003': 'Average Hourly Earnings - Private Sector',
        'CES0500000007': 'Average Weekly Hours - Private Sector',
        'CIS2010000000000I': 'Employment Cost Index (ECI) - Private Industry',
        'PRS85006093': 'Labor Productivity Index - Nonfarm Business',
    },
}

# Flat dictionary for backward compatibility with parser and call sites.
BLS_SERIES = {
    series_id: name
    for _, series_map in BLS_SERIES_CATEGORIES.items()
    for series_id, name in series_map.items()
}


class BLSDataLoader:
    """Handles API version routing, payload configuration, and data cleaning for BLS."""
    
    def __init__(self, api_key: Optional[str] = None):
        # Resolve key from parameter or environment, but ignore placeholder values.
        self.api_key = self._normalize_api_key(api_key or os.getenv('BLS_API_KEY'))

        # Select appropriate endpoint and version
        self.version = "v2" if self.api_key else "v1"
        # Base URL already contains /v1 or /v2 in BLSClient.
        self.base_endpoint = "/timeseries/data/"
        self.client = BLSClient(api_key=self.api_key)

    @staticmethod
    def _normalize_api_key(raw_key: Optional[str]) -> Optional[str]:
        """Normalize optional API key and treat template placeholders as missing."""
        if not raw_key:
            return None

        key = str(raw_key).strip()
        if not key:
            return None

        placeholders = {
            'your_bls_api_key_here',
            'your_api_key_here',
            'changeme',
            'change-me',
        }
        if key.lower() in placeholders:
            return None

        return key

    def _parse_date(self, year: str, period: str, exclude_averages: bool = True) -> Optional[datetime]:
        """
        Converts BLS period codes to datetime objects.
        Handles monthly (M01-M13), quarterly (Q01-Q05), semi-annual (S01-S03), and annual (A01).
        """
        try:
            yr = int(year)
            # Monthly
            if period.startswith('M'):
                month_num = int(period[1:])
                if 1 <= month_num <= 12:
                    return datetime(yr, month_num, 1)
                elif month_num == 13 and not exclude_averages:
                    return datetime(yr, 12, 31)  # Annual Average mapped to end of year
            # Quarterly
            elif period.startswith('Q'):
                q_num = int(period[1:])
                if 1 <= q_num <= 4:
                    month = (q_num - 1) * 3 + 1
                    return datetime(yr, month, 1)
                elif q_num == 5 and not exclude_averages:
                    return datetime(yr, 12, 31)  # Annual Average
            # Semi-Annual
            elif period.startswith('S'):
                s_num = int(period[1:])
                if s_num == 1:
                    return datetime(yr, 6, 30)
                elif s_num == 2:
                    return datetime(yr, 12, 31)
                elif s_num == 3 and not exclude_averages:
                    return datetime(yr, 12, 31)  # Annual Average
            # Annual
            elif period == 'A01':
                return datetime(yr, 12, 31)
        except (ValueError, IndexError):
            pass
        return None

    def _parse_value(self, value_str: str) -> Optional[float]:
        """Safely parses numeric string values, handling empty cells or dashes."""
        if not value_str or value_str.strip() in ('', '-', '.'):
            return None
        try:
            return float(value_str)
        except ValueError:
            logger.warning(f"Unable to parse numeric value: '{value_str}'")
            return None

    def _format_footnotes(self, footnotes: List[Dict[str, str]]) -> str:
        """Parses raw footnote arrays into a flat, comma-separated string."""
        return ",".join([f.get('text') for f in footnotes if isinstance(f, dict) and f.get('text')])

    def fetch_series(
        self,
        series_ids: List[str],
        start_year: int,
        end_year: int,
        exclude_averages: bool = True
    ) -> pd.DataFrame:
        """Executes the requests and formats the JSON results into a DataFrame."""
        logger.info(f"Requesting {len(series_ids)} series via BLS {self.version}")
        
        payload = {
            'seriesid': series_ids,
            'startyear': str(start_year),
            'endyear': str(end_year),
        }
        
        if self.api_key:
            payload['registrationkey'] = self.api_key

        try:
            response = self.client.post(
                self.base_endpoint,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            data = response.json()
            
            if data.get('status') != 'REQUEST_SUCCEEDED':
                logger.error(f"BLS API error: {data.get('message', 'Unknown error')}")
                return pd.DataFrame()
            
            records = []
            for series in data.get('Results', {}).get('series', []):
                series_id = series.get('seriesID', '')
                series_name = BLS_SERIES.get(series_id, series_id)
                
                for item in series.get('data', []):
                    dt = self._parse_date(item.get('year'), item.get('period'), exclude_averages)
                    if not dt:
                        continue
                    
                    val = self._parse_value(item.get('value', ''))
                    if val is None:
                        continue
                        
                    records.append({
                        'series_id': series_id,
                        'series_name': series_name,
                        'year': int(item.get('year', 0)),
                        'period': item.get('period', ''),
                        'value': val,
                        'date': dt,
                        'footnotes': self._format_footnotes(item.get('footnotes', []))
                    })
            
            df = pd.DataFrame(records)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values(['series_id', 'date']).reset_index(drop=True)
            
            logger.info(f"Successfully processed {len(df)} BLS records")
            return df
            
        except Exception as e:
            logger.error(f"Error communicating with BLS API: {e}")
            raise
        finally:
            self.client.close()


# --- Functional Wrappers (Maintained for Backward Compatibility) ---

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
    if start_year is None:
        start_year = datetime.now().year - 10
    if end_year is None:
        end_year = datetime.now().year

    loader = BLSDataLoader(api_key=api_key)
    return loader.fetch_series(series_ids, start_year, end_year)


def fetch_bls_unemployment() -> pd.DataFrame:
    """
    Fetch unemployment rate data from BLS.
    
    Returns:
        DataFrame with unemployment rate
    """
    logger.info("Fetching BLS unemployment rate")
    return fetch_bls_series(
        series_ids=['LNS14000000'],
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
        series_ids=['CUUR0000SA0', 'CUSR0000SA0'],
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