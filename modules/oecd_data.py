"""
OECD (Organisation for Economic Co-operation and Development) Data Loader

Fetches economic data from the OECD API:
https://data.oecd.org/api/

OECD provides:
- Leading indicators
- Productivity data
- Economic outlook
- Employment statistics
- Trade data for 38 member countries
"""

import pandas as pd
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import os
from modules.http_client import OECDClient

logger = logging.getLogger(__name__)


# OECD Dataset codes
OECD_DATASETS = {
    'MEI': 'Main Economic Indicators',
    'QNA': 'Quarterly National Accounts',
    'KEI': 'Key Economic Indicators',
    'EO': 'Economic Outlook',
}

# Popular OECD indicators
OECD_INDICATORS = {
    'CLI': 'Composite Leading Indicator',
    'LRHUTTTT': 'Unemployment Rate',
    'NAEXKP01': 'GDP (expenditure approach)',
    'PRMNTO01': 'Producer Price Index',
    'CPALTT01': 'Consumer Price Index',
}


def fetch_oecd_cli(countries: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Fetch Composite Leading Indicator (CLI) from OECD.
    
    The CLI is designed to provide early signals of turning points 
    in business cycles.
    
    Args:
        countries: List of OECD country codes. If None, fetches all OECD countries
        
    Returns:
        DataFrame with CLI data
    """
    logger.info("Fetching OECD Composite Leading Indicator")
    
    client = OECDClient()
    
    try:
        # OECD SDMX-JSON data structure
        # Format: /dataset/location/indicator/frequency
        if countries:
            location_str = '+'.join(countries)
        else:
            location_str = 'all'
        
        endpoint = f'/MEI_CLI/{location_str}/LOLITOAA_GYSA/M'
        
        response = client.get_json(endpoint)
        
        # Parse SDMX-JSON format
        if 'dataSets' not in response or not response['dataSets']:
            logger.warning("No CLI data returned from OECD")
            return pd.DataFrame()
        
        dataset = response['dataSets'][0]
        structure = response.get('structure', {})
        dimensions = structure.get('dimensions', {}).get('observation', [])
        
        # Extract dimension information
        time_dim = next((d for d in dimensions if d['id'] == 'TIME_PERIOD'), None)
        location_dim = next((d for d in dimensions if d['id'] == 'REF_AREA'), None)
        
        if not time_dim or not location_dim:
            logger.error("Could not parse OECD data structure")
            return pd.DataFrame()
        
        time_values = [v['id'] for v in time_dim.get('values', [])]
        location_values = [v['id'] for v in location_dim.get('values', [])]
        
        # Parse observations
        records = []
        observations = dataset.get('observations', {})
        
        for key, value in observations.items():
            indices = [int(x) for x in key.split(':')]
            
            if len(indices) >= 2:
                location_idx = indices[0]
                time_idx = indices[-1]
                
                if location_idx < len(location_values) and time_idx < len(time_values):
                    records.append({
                        'country_code': location_values[location_idx],
                        'period': time_values[time_idx],
                        'value': float(value[0]) if value and len(value) > 0 else None,
                        'indicator': 'CLI',
                        'indicator_name': 'Composite Leading Indicator',
                    })
        
        df = pd.DataFrame(records)
        
        if not df.empty:
            # Convert period to date
            df['date'] = pd.to_datetime(df['period'], format='%Y-%m', errors='coerce')
            df = df.dropna(subset=['date', 'value'])
        
        logger.info(f"Fetched {len(df)} OECD CLI records")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching OECD CLI: {e}")
        raise
    finally:
        client.close()


def fetch_oecd_productivity(countries: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Fetch productivity data from OECD.
    
    Args:
        countries: List of OECD country codes
        
    Returns:
        DataFrame with productivity data
    """
    logger.info("Fetching OECD productivity data")
    
    client = OECDClient()
    
    try:
        # Labour productivity growth
        if countries:
            location_str = '+'.join(countries)
        else:
            location_str = 'all'
        
        # Annual productivity growth
        endpoint = f'/PDB_GR/{location_str}/T_GDPEMP/A'
        
        response = client.get_json(endpoint)
        
        # Parse response (similar to CLI)
        if 'dataSets' not in response or not response['dataSets']:
            logger.warning("No productivity data returned from OECD")
            return pd.DataFrame()
        
        dataset = response['dataSets'][0]
        structure = response.get('structure', {})
        dimensions = structure.get('dimensions', {}).get('observation', [])
        
        time_dim = next((d for d in dimensions if d['id'] == 'TIME_PERIOD'), None)
        location_dim = next((d for d in dimensions if d['id'] == 'REF_AREA'), None)
        
        if not time_dim or not location_dim:
            logger.error("Could not parse OECD productivity data structure")
            return pd.DataFrame()
        
        time_values = [v['id'] for v in time_dim.get('values', [])]
        location_values = [v['id'] for v in location_dim.get('values', [])]
        
        records = []
        observations = dataset.get('observations', {})
        
        for key, value in observations.items():
            indices = [int(x) for x in key.split(':')]
            
            if len(indices) >= 2:
                location_idx = indices[0]
                time_idx = indices[-1]
                
                if location_idx < len(location_values) and time_idx < len(time_values):
                    records.append({
                        'country_code': location_values[location_idx],
                        'year': int(time_values[time_idx]),
                        'value': float(value[0]) if value and len(value) > 0 else None,
                        'indicator': 'PRODUCTIVITY',
                        'indicator_name': 'Labour Productivity Growth',
                    })
        
        df = pd.DataFrame(records)
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['year'].astype(str) + '-12-31')
            df = df.dropna(subset=['date', 'value'])
        
        logger.info(f"Fetched {len(df)} OECD productivity records")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching OECD productivity: {e}")
        raise
    finally:
        client.close()


def refresh_oecd_data(
    include_cli: bool = True,
    include_productivity: bool = True,
    countries: Optional[List[str]] = None
) -> int:
    """
    Refresh OECD data in the database.
    
    This is the main entry point called by schedulers.
    
    Args:
        include_cli: Whether to fetch Composite Leading Indicator
        include_productivity: Whether to fetch productivity data
        countries: List of country codes. If None, uses OECD members
        
    Returns:
        Number of records inserted
    """
    from modules.database.queries import insert_generic_data
    
    # Default to major OECD economies
    if countries is None:
        countries = ['USA', 'JPN', 'DEU', 'GBR', 'FRA', 'ITA', 'CAN', 'AUS', 'KOR', 'ESP']
    
    total_records = 0
    
    # Fetch CLI
    if include_cli:
        logger.info("Refreshing OECD CLI data")
        try:
            df = fetch_oecd_cli(countries=countries)
            if not df.empty:
                records = insert_generic_data(df, 'oecd_indicators')
                total_records += records
                logger.info(f"Inserted {records} OECD CLI records")
        except Exception as e:
            logger.error(f"Error refreshing OECD CLI: {e}")
    
    # Fetch productivity
    if include_productivity:
        logger.info("Refreshing OECD productivity data")
        try:
            df = fetch_oecd_productivity(countries=countries)
            if not df.empty:
                records = insert_generic_data(df, 'oecd_indicators')
                total_records += records
                logger.info(f"Inserted {records} OECD productivity records")
        except Exception as e:
            logger.error(f"Error refreshing OECD productivity: {e}")
    
    logger.info(f"Total OECD records inserted: {total_records}")
    return total_records
