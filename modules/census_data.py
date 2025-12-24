"""
US Census Bureau Data Loader

Fetches economic data from the Census Bureau API:
https://www.census.gov/data/developers/data-sets.html

Census Bureau provides:
- Retail sales data
- Housing starts and building permits
- International trade statistics
- Economic indicators
- Demographic data
"""

import pandas as pd
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
from modules.http_client import CensusBureauClient

logger = logging.getLogger(__name__)


# Census datasets
CENSUS_DATASETS = {
    'timeseries/eits/marts': 'Monthly Retail Trade Survey',
    'timeseries/eits/resconst': 'Residential Construction',
    'timeseries/intltrade/exports': 'International Trade Exports',
    'timeseries/intltrade/imports': 'International Trade Imports',
}


def fetch_census_retail_sales(
    api_key: Optional[str] = None,
    start_year: Optional[int] = None
) -> pd.DataFrame:
    """
    Fetch retail sales data from Census Bureau.
    
    Args:
        api_key: Census API key
        start_year: Start year (default: 5 years ago)
        
    Returns:
        DataFrame with retail sales data
    """
    logger.info("Fetching Census retail sales data")
    
    # Get API key from environment if not provided
    if api_key is None:
        api_key = os.getenv('CENSUS_API_KEY')
    
    if not api_key:
        raise ValueError("Census API key is required")
    
    client = CensusBureauClient(api_key=api_key)
    
    # Set default start year
    if start_year is None:
        start_year = datetime.now().year - 5
    
    try:
        # Monthly Retail Trade Survey endpoint
        endpoint = '/timeseries/eits/marts'
        
        # Request parameters
        params = {
            'get': 'cell_value,data_type_code,time_slot_id,category_code,seasonally_adj',
            'time': f'from {start_year}',
        }
        
        response = client.get_json(endpoint, params=params)
        
        # Census API returns array with header row
        if not response or len(response) < 2:
            logger.warning("No retail sales data returned from Census")
            return pd.DataFrame()
        
        # First row is headers
        headers = response[0]
        data_rows = response[1:]
        
        # Create DataFrame
        df = pd.DataFrame(data_rows, columns=headers)
        
        # Parse and clean data
        records = []
        for _, row in df.iterrows():
            try:
                value = float(row.get('cell_value', 0))
                time_slot = row.get('time_slot_id', '')
                category = row.get('category_code', '')
                seasonally_adj = row.get('seasonally_adj', '')
                
                # Parse time slot (YYYYMM format)
                if len(time_slot) == 6:
                    year = int(time_slot[:4])
                    month = int(time_slot[4:6])
                    date = f"{year}-{month:02d}-01"
                    
                    records.append({
                        'date': date,
                        'category': category,
                        'value': value,
                        'seasonally_adjusted': seasonally_adj == 'yes',
                        'indicator': 'RETAIL_SALES',
                    })
            except (ValueError, TypeError):
                continue
        
        result_df = pd.DataFrame(records)
        
        if not result_df.empty:
            result_df['date'] = pd.to_datetime(result_df['date'])
            result_df = result_df.sort_values('date')
        
        logger.info(f"Fetched {len(result_df)} retail sales records")
        return result_df
        
    except Exception as e:
        logger.error(f"Error fetching Census retail sales: {e}")
        raise
    finally:
        client.close()


def fetch_census_housing_starts(
    api_key: Optional[str] = None,
    start_year: Optional[int] = None
) -> pd.DataFrame:
    """
    Fetch housing starts and building permits data from Census Bureau.
    
    Args:
        api_key: Census API key
        start_year: Start year (default: 5 years ago)
        
    Returns:
        DataFrame with housing construction data
    """
    logger.info("Fetching Census housing starts data")
    
    # Get API key from environment if not provided
    if api_key is None:
        api_key = os.getenv('CENSUS_API_KEY')
    
    if not api_key:
        raise ValueError("Census API key is required")
    
    client = CensusBureauClient(api_key=api_key)
    
    # Set default start year
    if start_year is None:
        start_year = datetime.now().year - 5
    
    try:
        # Residential Construction endpoint
        endpoint = '/timeseries/eits/resconst'
        
        params = {
            'get': 'cell_value,data_type_code,time_slot_id,category_code,seasonally_adj',
            'time': f'from {start_year}',
        }
        
        response = client.get_json(endpoint, params=params)
        
        if not response or len(response) < 2:
            logger.warning("No housing data returned from Census")
            return pd.DataFrame()
        
        headers = response[0]
        data_rows = response[1:]
        
        df = pd.DataFrame(data_rows, columns=headers)
        
        records = []
        for _, row in df.iterrows():
            try:
                value = float(row.get('cell_value', 0))
                time_slot = row.get('time_slot_id', '')
                category = row.get('category_code', '')
                seasonally_adj = row.get('seasonally_adj', '')
                
                # Parse time slot
                if len(time_slot) == 6:
                    year = int(time_slot[:4])
                    month = int(time_slot[4:6])
                    date = f"{year}-{month:02d}-01"
                    
                    records.append({
                        'date': date,
                        'category': category,
                        'value': value,
                        'seasonally_adjusted': seasonally_adj == 'yes',
                        'indicator': 'HOUSING_STARTS',
                    })
            except (ValueError, TypeError):
                continue
        
        result_df = pd.DataFrame(records)
        
        if not result_df.empty:
            result_df['date'] = pd.to_datetime(result_df['date'])
            result_df = result_df.sort_values('date')
        
        logger.info(f"Fetched {len(result_df)} housing starts records")
        return result_df
        
    except Exception as e:
        logger.error(f"Error fetching Census housing data: {e}")
        raise
    finally:
        client.close()


def fetch_census_trade(
    api_key: Optional[str] = None,
    start_year: Optional[int] = None,
    trade_type: str = 'exports'
) -> pd.DataFrame:
    """
    Fetch international trade data from Census Bureau.
    
    Args:
        api_key: Census API key
        start_year: Start year (default: 5 years ago)
        trade_type: 'exports' or 'imports'
        
    Returns:
        DataFrame with trade data
    """
    logger.info(f"Fetching Census {trade_type} data")
    
    # Get API key from environment if not provided
    if api_key is None:
        api_key = os.getenv('CENSUS_API_KEY')
    
    if not api_key:
        raise ValueError("Census API key is required")
    
    client = CensusBureauClient(api_key=api_key)
    
    # Set default start year
    if start_year is None:
        start_year = datetime.now().year - 5
    
    try:
        # Trade endpoint
        endpoint = f'/timeseries/intltrade/{trade_type}'
        
        params = {
            'get': 'GEN_VAL_MO,time_period',
            'time': f'from {start_year}',
        }
        
        response = client.get_json(endpoint, params=params)
        
        if not response or len(response) < 2:
            logger.warning(f"No {trade_type} data returned from Census")
            return pd.DataFrame()
        
        headers = response[0]
        data_rows = response[1:]
        
        df = pd.DataFrame(data_rows, columns=headers)
        
        records = []
        for _, row in df.iterrows():
            try:
                value = float(row.get('GEN_VAL_MO', 0))
                time_period = row.get('time_period', '')
                
                # Parse time period (YYYY-MM format)
                if '-' in time_period:
                    date = f"{time_period}-01"
                    
                    records.append({
                        'date': date,
                        'value': value,
                        'indicator': trade_type.upper(),
                    })
            except (ValueError, TypeError):
                continue
        
        result_df = pd.DataFrame(records)
        
        if not result_df.empty:
            result_df['date'] = pd.to_datetime(result_df['date'])
            result_df = result_df.sort_values('date')
        
        logger.info(f"Fetched {len(result_df)} {trade_type} records")
        return result_df
        
    except Exception as e:
        logger.error(f"Error fetching Census {trade_type} data: {e}")
        raise
    finally:
        client.close()


def refresh_census_data(
    include_retail: bool = True,
    include_housing: bool = True,
    include_trade: bool = True,
    api_key: Optional[str] = None
) -> int:
    """
    Refresh Census Bureau data in the database.
    
    This is the main entry point called by schedulers.
    
    Args:
        include_retail: Whether to fetch retail sales
        include_housing: Whether to fetch housing starts
        include_trade: Whether to fetch trade data
        api_key: Census API key
        
    Returns:
        Number of records inserted
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
        try:
            # Fetch both exports and imports
            for trade_type in ['exports', 'imports']:
                df = fetch_census_trade(api_key=api_key, trade_type=trade_type)
                if not df.empty:
                    records = insert_generic_data(df, 'census_data')
                    total_records += records
                    logger.info(f"Inserted {records} Census {trade_type} records")
        except Exception as e:
            logger.error(f"Error refreshing Census trade data: {e}")
    
    logger.info(f"Total Census records inserted: {total_records}")
    return total_records
