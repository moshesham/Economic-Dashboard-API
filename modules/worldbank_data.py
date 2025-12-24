"""
World Bank API Data Loader

Fetches economic indicators from the World Bank API:
https://datahelpdesk.worldbank.org/knowledgebase/topics/125589

World Bank provides:
- 1,400+ economic indicators
- Data for 217 countries and regions
- Historical data back to 1960 for many indicators
- Development indicators, poverty statistics, trade data
"""

import pandas as pd
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import os
from modules.http_client import WorldBankClient

logger = logging.getLogger(__name__)


# Popular World Bank indicator codes
POPULAR_INDICATORS = {
    'NY.GDP.MKTP.CD': 'GDP (current US$)',
    'NY.GDP.MKTP.KD.ZG': 'GDP growth (annual %)',
    'NY.GDP.PCAP.CD': 'GDP per capita (current US$)',
    'NY.GDP.PCAP.KD.ZG': 'GDP per capita growth (annual %)',
    'FP.CPI.TOTL.ZG': 'Inflation, consumer prices (annual %)',
    'SL.UEM.TOTL.ZS': 'Unemployment, total (% of total labor force)',
    'NE.EXP.GNFS.ZS': 'Exports of goods and services (% of GDP)',
    'NE.IMP.GNFS.ZS': 'Imports of goods and services (% of GDP)',
    'GC.DOD.TOTL.GD.ZS': 'Central government debt, total (% of GDP)',
    'SP.POP.TOTL': 'Population, total',
    'SI.POV.GINI': 'Gini index',
}


def fetch_worldbank_indicator(
    indicator: str,
    countries: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """
    Fetch World Bank indicator data for specified countries.
    
    Args:
        indicator: World Bank indicator code (e.g., 'NY.GDP.MKTP.CD')
        countries: List of country ISO3 codes (e.g., ['USA', 'CHN']). 
                  If None, fetches for all countries.
        start_date: Optional start year (e.g., '2010')
        end_date: Optional end year (e.g., '2023')
        
    Returns:
        DataFrame with columns: country_code, country_name, indicator_code, 
                               indicator_name, year, value
    """
    logger.info(f"Fetching World Bank indicator: {indicator}")
    
    client = WorldBankClient()
    
    try:
        # Build URL path
        if countries:
            country_str = ';'.join(countries)
        else:
            country_str = 'all'
        
        # World Bank API path: /v2/country/{countries}/indicator/{indicator}
        endpoint = f"/country/{country_str}/indicator/{indicator}"
        
        # Build query parameters
        params = {}
        if start_date:
            params['date'] = f"{start_date}:{end_date or datetime.now().year}"
        
        # Fetch data (World Bank API paginates results)
        all_data = []
        page = 1
        
        while True:
            params['page'] = page
            response = client.get_json(endpoint, params=params)
            
            # World Bank returns [metadata, data] array
            if not isinstance(response, list) or len(response) < 2:
                break
            
            metadata = response[0]
            data = response[1]
            
            if not data:
                break
            
            all_data.extend(data)
            
            # Check if there are more pages
            if metadata.get('page', 1) >= metadata.get('pages', 1):
                break
            
            page += 1
        
        if not all_data:
            logger.warning(f"No data returned for indicator {indicator}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        records = []
        for item in all_data:
            if item.get('value') is not None:  # Skip null values
                records.append({
                    'country_code': item.get('countryiso3code', ''),
                    'country_name': item.get('country', {}).get('value', ''),
                    'indicator_code': item.get('indicator', {}).get('id', ''),
                    'indicator_name': item.get('indicator', {}).get('value', ''),
                    'year': int(item.get('date', 0)),
                    'value': float(item.get('value', 0)),
                    'unit': item.get('unit', ''),
                    'decimal': item.get('decimal', 0),
                })
        
        df = pd.DataFrame(records)
        
        # Convert year to date
        if not df.empty and 'year' in df.columns:
            df['date'] = pd.to_datetime(df['year'].astype(str) + '-12-31')
        
        logger.info(f"Fetched {len(df)} records for indicator {indicator}")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching World Bank data: {e}")
        raise
    finally:
        client.close()


def fetch_worldbank_multiple_indicators(
    indicators: List[str],
    countries: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """
    Fetch multiple World Bank indicators.
    
    Args:
        indicators: List of World Bank indicator codes
        countries: List of country ISO3 codes
        start_date: Optional start year
        end_date: Optional end year
        
    Returns:
        Combined DataFrame with all indicators
    """
    all_data = []
    
    for indicator in indicators:
        try:
            df = fetch_worldbank_indicator(
                indicator=indicator,
                countries=countries,
                start_date=start_date,
                end_date=end_date
            )
            if not df.empty:
                all_data.append(df)
        except Exception as e:
            logger.error(f"Error fetching indicator {indicator}: {e}")
            continue
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    
    return pd.DataFrame()


def fetch_worldbank_countries() -> pd.DataFrame:
    """
    Fetch list of all countries from World Bank API.
    
    Returns:
        DataFrame with country information
    """
    logger.info("Fetching World Bank country list")
    
    client = WorldBankClient()
    
    try:
        response = client.get_json('/country', params={'per_page': '500'})
        
        if not isinstance(response, list) or len(response) < 2:
            return pd.DataFrame()
        
        data = response[1]
        
        records = []
        for item in data:
            records.append({
                'country_code': item.get('id', ''),
                'country_iso2': item.get('iso2Code', ''),
                'country_name': item.get('name', ''),
                'region': item.get('region', {}).get('value', ''),
                'income_level': item.get('incomeLevel', {}).get('value', ''),
                'capital_city': item.get('capitalCity', ''),
                'longitude': item.get('longitude', ''),
                'latitude': item.get('latitude', ''),
            })
        
        df = pd.DataFrame(records)
        logger.info(f"Fetched {len(df)} countries from World Bank")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching World Bank countries: {e}")
        raise
    finally:
        client.close()


def refresh_worldbank_data(
    indicators: Optional[List[str]] = None,
    countries: Optional[List[str]] = None,
    start_year: Optional[str] = None
) -> int:
    """
    Refresh World Bank data in the database.
    
    This is the main entry point called by schedulers.
    
    Args:
        indicators: List of indicator codes to fetch. If None, uses popular indicators
        countries: List of country codes. If None, fetches major economies
        start_year: Start year. If None, fetches last 10 years
        
    Returns:
        Number of records inserted
    """
    from modules.database.queries import insert_generic_data
    
    # Default to popular indicators
    if indicators is None:
        indicators = list(POPULAR_INDICATORS.keys())[:5]  # Top 5 indicators
    
    # Default to major economies
    if countries is None:
        countries = ['USA', 'CHN', 'JPN', 'DEU', 'IND', 'GBR', 'FRA', 'BRA', 'ITA', 'CAN']
    
    # Default to last 10 years
    if start_year is None:
        start_year = str(datetime.now().year - 10)
    
    end_year = str(datetime.now().year)
    
    logger.info(f"Refreshing World Bank data: {len(indicators)} indicators, {len(countries)} countries")
    
    df = fetch_worldbank_multiple_indicators(
        indicators=indicators,
        countries=countries,
        start_date=start_year,
        end_date=end_year
    )
    
    if not df.empty:
        records_inserted = insert_generic_data(df, 'worldbank_indicators')
        logger.info(f"Inserted {records_inserted} World Bank records")
        return records_inserted
    
    return 0
