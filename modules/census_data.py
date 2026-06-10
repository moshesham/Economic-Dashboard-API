"""
US Census Bureau Data Loader

Fetches economic and international trade data from the US Census Bureau API:
https://www.census.gov/data/developers/data-sets/economic-indicators.html

Census Bureau provides key monthly macroeconomic indicators under EITS (Economic Indicator Time Series):
- Retail Sales (Monthly Retail Trade Survey - MARTS)
- Housing Starts and Building Permits (Residential Construction - RESCONST)
- International Trade Statistics (Exports & Imports via the Harmonized System - HS)
"""

import pandas as pd
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import os

logger = logging.getLogger(__name__)


# Census datasets endpoints (updated based on Census guidelines)
CENSUS_DATASETS = {
    'timeseries/eits/marts': 'Monthly Retail Trade Survey (MARTS)',
    'timeseries/eits/resconst': 'Residential Construction (RESCONST)',
    'timeseries/intltrade/exports/hs': 'International Trade Exports (Harmonized System)',
    'timeseries/intltrade/imports/hs': 'International Trade Imports (Harmonized System)',
}


class CensusBureauDataLoader:
    """
    A unified loader to fetch economic, construction, and international trade 
    data from the US Census Bureau API.
    """

    def __init__(self, api_key: Optional[str] = None):
        # Resolve Census API key
        self.api_key = api_key or os.getenv('CENSUS_API_KEY')
        if not self.api_key:
            raise ValueError("Census API key is required. Pass it to the loader or set CENSUS_API_KEY in your environment.")

        # Try to import and instantiate the project-specific CensusBureauClient.
        # Fall back to a standard requests session if not available.
        try:
            from modules.http_client import CensusBureauClient
            self.client = CensusBureauClient(api_key=self.api_key)
            self._is_custom_client = True
            logger.debug("Successfully initialized loader using custom CensusBureauClient.")
        except ImportError:
            import requests
            class StandardCensusClient:
                def __init__(self, key: str):
                    self.key = key
                    self.session = requests.Session()

                def get_json(self, endpoint: str, params: Dict[str, Any]) -> Any:
                    url = f"https://api.census.gov/data{endpoint}"
                    query_params = params.copy()
                    query_params['key'] = self.key
                    response = self.session.get(url, params=query_params)
                    response.raise_for_status()
                    return response.json()

                def close(self):
                    self.session.close()

            self.client = StandardCensusClient(key=self.api_key)
            self._is_custom_client = False
            logger.debug("Successfully initialized loader using fallback standard requests client.")

    def close(self):
        """Clean up HTTP client session."""
        try:
            self.client.close()
        except Exception as e:
            logger.debug(f"Error closing Census client: {e}")

    def fetch_eits_data(self, endpoint: str, start_year: int) -> pd.DataFrame:
        """
        Generic helper to fetch data from the Economic Indicator Time Series (EITS).
        """
        params = {
            'get': 'cell_value,data_type_code,time_slot_id,category_code,seasonally_adj',
            'time': f'from {start_year}',
        }

        response = self.client.get_json(endpoint, params=params)

        if not response or len(response) < 2:
            logger.warning(f"No EITS data returned from endpoint: {endpoint}")
            return pd.DataFrame()

        headers = response[0]
        data_rows = response[1:]
        df = pd.DataFrame(data_rows, columns=headers)

        records = []
        for _, row in df.iterrows():
            try:
                # Filter out suppressed values (e.g., (D), (S), (NA)) gracefully
                val_str = str(row.get('cell_value', '0')).strip()
                value = float(val_str)
                
                category = row.get('category_code', '')
                seasonally_adj = row.get('seasonally_adj', '')

                # Extract and parse the standard date from 'time' or fallback to 'time_slot_id'
                date_str = None
                time_val = row.get('time') or row.get('time_period')
                
                if time_val:
                    time_str = str(time_val).strip()
                    if '-' in time_str:
                        # e.g., '2013-01'
                        date_str = f"{time_str}-01"
                    elif len(time_str) == 4 and time_str.isdigit():
                        # e.g., '2013'
                        date_str = f"{time_str}-01-01"
                
                # Legacy fallback to time_slot_id if time_val was missing/malformed but time_slot_id is YYYYMM
                if not date_str:
                    time_slot = str(row.get('time_slot_id', ''))
                    if len(time_slot) == 6 and time_slot.isdigit():
                        year = int(time_slot[:4])
                        month = int(time_slot[4:6])
                        if 1 <= month <= 12:
                            date_str = f"{year}-{month:02d}-01"

                if date_str:
                    records.append({
                        'date': date_str,
                        'category': category,
                        'value': value,
                        'seasonally_adjusted': seasonally_adj.lower() == 'yes',
                    })
            except (ValueError, TypeError):
                continue

        result_df = pd.DataFrame(records)
        if not result_df.empty:
            result_df['date'] = pd.to_datetime(result_df['date'])
            result_df = result_df.sort_values('date')
        
        return result_df

    def fetch_trade_data(self, trade_type: str, start_year: int) -> pd.DataFrame:
        """
        Generic helper to fetch aggregate International Trade data from HS endpoints.
        """
        # Validate and configure trade type endpoints
        trade_type_clean = trade_type.lower().strip()
        if trade_type_clean == 'exports':
            endpoint = '/timeseries/intltrade/exports/hs'
            val_col = 'ALL_VAL_MO'  # Monthly total export value
        elif trade_type_clean == 'imports':
            endpoint = '/timeseries/intltrade/imports/hs'
            val_col = 'GEN_VAL_MO'  # Monthly general import value
        else:
            raise ValueError("trade_type must be either 'exports' or 'imports'")

        params = {
            'get': val_col,
            'time': f'from {start_year}',
        }

        response = self.client.get_json(endpoint, params=params)

        if not response or len(response) < 2:
            logger.warning(f"No trade data returned from endpoint: {endpoint}")
            return pd.DataFrame()

        headers = response[0]
        data_rows = response[1:]
        df = pd.DataFrame(data_rows, columns=headers)

        records = []
        for _, row in df.iterrows():
            try:
                # Handle non-numeric or suppressed values safely
                val_str = str(row.get(val_col, '0')).strip()
                value = float(val_str)

                time_val = row.get('time') or row.get('time_period') or ''
                if '-' in time_val:
                    # e.g., '2021-11' -> '2021-11-01'
                    date_str = f"{time_val}-01"
                    records.append({
                        'date': date_str,
                        'value': value,
                        'indicator': trade_type_clean.upper(),
                        'category': '',
                    })
            except (ValueError, TypeError):
                continue

        result_df = pd.DataFrame(records)
        if not result_df.empty:
            result_df['date'] = pd.to_datetime(result_df['date'])
            result_df = result_df.sort_values('date')

        return result_df


# ==========================================
# Standalone Functions calling the Loader Class
# ==========================================

def fetch_census_retail_sales(
    api_key: Optional[str] = None,
    start_year: Optional[int] = None
) -> pd.DataFrame:
    """
    Fetch retail sales data from the Census MARTS endpoint.
    """
    logger.info("Fetching Census retail sales data")
    
    if start_year is None:
        start_year = datetime.now().year - 5

    loader = CensusBureauDataLoader(api_key=api_key)
    try:
        df = loader.fetch_eits_data('/timeseries/eits/marts', start_year)
        if not df.empty:
            df['indicator'] = 'RETAIL_SALES'
        logger.info(f"Fetched {len(df)} retail sales records")
        return df
    finally:
        loader.close()


def fetch_census_housing_starts(
    api_key: Optional[str] = None,
    start_year: Optional[int] = None
) -> pd.DataFrame:
    """
    Fetch housing starts and building permits from the Census RESCONST endpoint.
    """
    logger.info("Fetching Census housing starts data")
    
    if start_year is None:
        start_year = datetime.now().year - 5

    loader = CensusBureauDataLoader(api_key=api_key)
    try:
        df = loader.fetch_eits_data('/timeseries/eits/resconst', start_year)
        if not df.empty:
            df['indicator'] = 'HOUSING_STARTS'
        logger.info(f"Fetched {len(df)} housing starts records")
        return df
    finally:
        loader.close()


def fetch_census_trade(
    api_key: Optional[str] = None,
    start_year: Optional[int] = None,
    trade_type: str = 'exports'
) -> pd.DataFrame:
    """
    Fetch international trade data from the correct Harmonized System (HS) endpoints.
    """
    logger.info(f"Fetching Census trade {trade_type} data")
    
    if start_year is None:
        start_year = datetime.now().year - 5

    loader = CensusBureauDataLoader(api_key=api_key)
    try:
        df = loader.fetch_trade_data(trade_type, start_year)
        logger.info(f"Fetched {len(df)} {trade_type} trade records")
        return df
    finally:
        loader.close()


def refresh_census_data(
    include_retail: bool = True,
    include_housing: bool = True,
    include_trade: bool = True,
    api_key: Optional[str] = None
) -> int:
    """
    Refresh Census Bureau data in the database.
    """
    from modules.database.queries import insert_generic_data
    
    total_records = 0
    
    # Fetch retail sales
    if include_retail:
        logger.info("Refreshing Census retail sales data")
        try:
            df = fetch_census_retail_sales(api_key=api_key)
            if not df.empty:
                records = insert_generic_data(df, 'census_data')
                total_records += records
                logger.info(f"Inserted {records} Census retail records")
        except Exception as e:
            logger.error(f"Error refreshing Census retail data: {e}")
    
    # Fetch housing starts
    if include_housing:
        logger.info("Refreshing Census housing starts data")
        try:
            df = fetch_census_housing_starts(api_key=api_key)
            if not df.empty:
                records = insert_generic_data(df, 'census_data')
                total_records += records
                logger.info(f"Inserted {records} Census housing records")
        except Exception as e:
            logger.error(f"Error refreshing Census housing data: {e}")
    
    # Fetch trade data
    if include_trade:
        logger.info("Refreshing Census trade data")
        for trade_type in ['exports', 'imports']:
            try:
                df = fetch_census_trade(api_key=api_key, trade_type=trade_type)
                if not df.empty:
                    records = insert_generic_data(df, 'census_data')
                    total_records += records
                    logger.info(f"Inserted {records} Census {trade_type} records")
            except Exception as e:
                logger.error(f"Error refreshing Census {trade_type} data: {e}")
                continue
    
    logger.info(f"Total Census records inserted: {total_records}")
    return total_records
