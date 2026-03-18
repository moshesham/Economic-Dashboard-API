"""
EIA (Energy Information Administration) Data Loader

Fetches energy data from the EIA API:
https://www.eia.gov/opendata/

EIA provides:
- Crude oil prices and inventories
- Natural gas prices and storage
- Electricity prices and generation
- Coal production and consumption
- Renewable energy statistics
"""

import pandas as pd
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
from modules.http_client import EIAClient

logger = logging.getLogger(__name__)


# Popular EIA series
EIA_SERIES = {
    # Crude Oil
    'PET.RWTC.D': 'Crude Oil WTI Spot Price ($/barrel)',
    'PET.RBRTE.D': 'Crude Oil Brent Spot Price ($/barrel)',
    'PET.WCESTUS1.W': 'US Crude Oil Stocks (thousand barrels)',
    
    # Natural Gas
    'NG.RNGWHHD.D': 'Natural Gas Henry Hub Spot Price ($/MMBtu)',
    'NG.NW2_EPG0_SWO_R48_BCF.W': 'Natural Gas Storage (Bcf)',
    
    # Electricity
    'ELEC.PRICE.US-ALL.M': 'Average Retail Electricity Price (cents/kWh)',
    'ELEC.GEN.ALL-US-99.M': 'Net Electricity Generation (MWh)',
    
    # Gasoline
    'PET.EMM_EPM0_PTE_NUS_DPG.W': 'Gasoline Retail Prices ($/gallon)',
}


def fetch_eia_series(
    series_id: str,
    api_key: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """
    Fetch EIA data series.
    
    Args:
        series_id: EIA series ID
        api_key: EIA API key
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        
    Returns:
        DataFrame with EIA data
    """
    logger.info(f"Fetching EIA series: {series_id}")
    
    # Get API key from environment if not provided
    if api_key is None:
        api_key = os.getenv('EIA_API_KEY')
    
    if not api_key:
        raise ValueError("EIA API key is required")
    
    client = EIAClient(api_key=api_key)
    
    try:
        # EIA API v2 endpoint structure
        # /series/?series_id={series_id}
        endpoint = '/series/'
        
        params = {
            'api_key': api_key,
            'series_id': series_id,
        }
        
        if start_date:
            params['start'] = start_date
        if end_date:
            params['end'] = end_date
        
        response = client.get_json(endpoint, params=params)
        
        # Parse EIA response
        if 'response' not in response:
            logger.warning(f"No data returned for series {series_id}")
            return pd.DataFrame()
        
        series_data = response['response'].get('data', [])
        
        if not series_data:
            logger.warning(f"Empty data for series {series_id}")
            return pd.DataFrame()
        
        # Parse data points
        records = []
        for item in series_data:
            try:
                period = item.get('period', '')
                value = item.get('value', None)
                
                if value is not None:
                    # Parse period based on frequency
                    # Daily: YYYY-MM-DD
                    # Weekly: YYYY-MM-DD
                    # Monthly: YYYY-MM
                    # Annual: YYYY
                    
                    if len(period) == 10:  # Daily/Weekly
                        date = period
                    elif len(period) == 7:  # Monthly (YYYY-MM)
                        date = f"{period}-01"
                    elif len(period) == 4:  # Annual
                        date = f"{period}-12-31"
                    else:
                        continue
                    
                    records.append({
                        'series_id': series_id,
                        'series_name': EIA_SERIES.get(series_id, series_id),
                        'period': period,
                        'value': float(value),
                        'date': date,
                    })
            except (ValueError, TypeError, KeyError):
                continue
        
        df = pd.DataFrame(records)
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
        
        logger.info(f"Fetched {len(df)} records for EIA series {series_id}")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching EIA series {series_id}: {e}")
        raise
    finally:
        client.close()


def fetch_eia_crude_oil_prices(api_key: Optional[str] = None) -> pd.DataFrame:
    """
    Fetch crude oil prices (WTI and Brent).
    
    Args:
        api_key: EIA API key
        
    Returns:
        DataFrame with crude oil prices
    """
    logger.info("Fetching EIA crude oil prices")
    
    all_data = []
    
    for series_id in ['PET.RWTC.D', 'PET.RBRTE.D']:
        try:
            df = fetch_eia_series(series_id=series_id, api_key=api_key)
            if not df.empty:
                all_data.append(df)
        except Exception as e:
            logger.error(f"Error fetching {series_id}: {e}")
            continue
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    
    return pd.DataFrame()


def fetch_eia_natural_gas(api_key: Optional[str] = None) -> pd.DataFrame:
    """
    Fetch natural gas prices and storage.
    
    Args:
        api_key: EIA API key
        
    Returns:
        DataFrame with natural gas data
    """
    logger.info("Fetching EIA natural gas data")
    
    all_data = []
    
    for series_id in ['NG.RNGWHHD.D', 'NG.NW2_EPG0_SWO_R48_BCF.W']:
        try:
            df = fetch_eia_series(series_id=series_id, api_key=api_key)
            if not df.empty:
                all_data.append(df)
        except Exception as e:
            logger.error(f"Error fetching {series_id}: {e}")
            continue
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    
    return pd.DataFrame()


def fetch_eia_electricity(api_key: Optional[str] = None) -> pd.DataFrame:
    """
    Fetch electricity prices and generation.
    
    Args:
        api_key: EIA API key
        
    Returns:
        DataFrame with electricity data
    """
    logger.info("Fetching EIA electricity data")
    
    all_data = []
    
    for series_id in ['ELEC.PRICE.US-ALL.M', 'ELEC.GEN.ALL-US-99.M']:
        try:
            df = fetch_eia_series(series_id=series_id, api_key=api_key)
            if not df.empty:
                all_data.append(df)
        except Exception as e:
            logger.error(f"Error fetching {series_id}: {e}")
            continue
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    
    return pd.DataFrame()


def fetch_eia_gasoline(api_key: Optional[str] = None) -> pd.DataFrame:
    """
    Fetch gasoline retail prices.
    
    Args:
        api_key: EIA API key
        
    Returns:
        DataFrame with gasoline prices
    """
    logger.info("Fetching EIA gasoline prices")
    
    return fetch_eia_series(
        series_id='PET.EMM_EPM0_PTE_NUS_DPG.W',
        api_key=api_key
    )


def refresh_eia_data(
    include_oil: bool = True,
    include_gas: bool = True,
    include_electricity: bool = True,
    include_gasoline: bool = True,
    api_key: Optional[str] = None
) -> int:
    """
    Refresh EIA data in the database.
    
    This is the main entry point called by schedulers.
    
    Args:
        include_oil: Whether to fetch crude oil data
        include_gas: Whether to fetch natural gas data
        include_electricity: Whether to fetch electricity data
        include_gasoline: Whether to fetch gasoline data
        api_key: EIA API key
        
    Returns:
        Number of records inserted
    """
    from modules.database.queries import insert_generic_data
    
    total_records = 0
    
    # Fetch crude oil
    if include_oil:
        logger.info("Refreshing EIA crude oil data")
        try:
            df = fetch_eia_crude_oil_prices(api_key=api_key)
            if not df.empty:
                records = insert_generic_data(df, 'eia_data')
                total_records += records
                logger.info(f"Inserted {records} EIA crude oil records")
        except Exception as e:
            logger.error(f"Error refreshing EIA crude oil: {e}")
    
    # Fetch natural gas
    if include_gas:
        logger.info("Refreshing EIA natural gas data")
        try:
            df = fetch_eia_natural_gas(api_key=api_key)
            if not df.empty:
                records = insert_generic_data(df, 'eia_data')
                total_records += records
                logger.info(f"Inserted {records} EIA natural gas records")
        except Exception as e:
            logger.error(f"Error refreshing EIA natural gas: {e}")
    
    # Fetch electricity
    if include_electricity:
        logger.info("Refreshing EIA electricity data")
        try:
            df = fetch_eia_electricity(api_key=api_key)
            if not df.empty:
                records = insert_generic_data(df, 'eia_data')
                total_records += records
                logger.info(f"Inserted {records} EIA electricity records")
        except Exception as e:
            logger.error(f"Error refreshing EIA electricity: {e}")
    
    # Fetch gasoline
    if include_gasoline:
        logger.info("Refreshing EIA gasoline data")
        try:
            df = fetch_eia_gasoline(api_key=api_key)
            if not df.empty:
                records = insert_generic_data(df, 'eia_data')
                total_records += records
                logger.info(f"Inserted {records} EIA gasoline records")
        except Exception as e:
            logger.error(f"Error refreshing EIA gasoline: {e}")
    
    logger.info(f"Total EIA records inserted: {total_records}")
    return total_records
