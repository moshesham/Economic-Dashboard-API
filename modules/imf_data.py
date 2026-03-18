"""
IMF (International Monetary Fund) Data Loader

Fetches economic and financial data from the IMF Data API:
https://www.imf.org/external/datamapper/api/help

IMF provides:
- Exchange rates
- International Financial Statistics (IFS)
- World Economic Outlook (WEO)
- Balance of Payments
- Government Finance Statistics
"""

import pandas as pd
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
from modules.http_client import IMFClient

logger = logging.getLogger(__name__)


# IMF Dataset codes
IMF_DATASETS = {
    'IFS': 'International Financial Statistics',
    'BOP': 'Balance of Payments',
    'GFSR': 'Global Financial Stability Report',
    'WEO': 'World Economic Outlook',
    'FSI': 'Financial Soundness Indicators',
}


def fetch_imf_exchange_rates(countries: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Fetch exchange rates from IMF.
    
    Args:
        countries: List of country ISO codes. If None, fetches major currencies
        
    Returns:
        DataFrame with exchange rate data
    """
    logger.info("Fetching IMF exchange rates")
    
    client = IMFClient()
    
    try:
        # IMF uses indicator codes for exchange rates
        # ENDA_XDC_USD_RATE = End of period exchange rate to USD
        endpoint = '/ENDA_XDC_USD_RATE'
        
        if countries:
            country_str = ','.join(countries)
            endpoint += f'/{country_str}'
        
        response = client.get_json(endpoint)
        
        # Parse IMF response
        if 'values' not in response:
            logger.warning("No exchange rate data returned from IMF")
            return pd.DataFrame()
        
        records = []
        for country_code, data in response['values'].items():
            for year, value in data.items():
                if value and value != '':
                    records.append({
                        'country_code': country_code,
                        'year': int(year),
                        'exchange_rate': float(value),
                        'indicator': 'ENDA_XDC_USD_RATE',
                        'indicator_name': 'Exchange Rate to USD',
                    })
        
        df = pd.DataFrame(records)
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['year'].astype(str) + '-12-31')
        
        logger.info(f"Fetched {len(df)} IMF exchange rate records")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching IMF exchange rates: {e}")
        raise
    finally:
        client.close()


def fetch_imf_indicator(
    indicator: str,
    countries: Optional[List[str]] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None
) -> pd.DataFrame:
    """
    Fetch IMF indicator data.
    
    Args:
        indicator: IMF indicator code
        countries: List of country ISO codes
        start_year: Start year
        end_year: End year
        
    Returns:
        DataFrame with indicator data
    """
    logger.info(f"Fetching IMF indicator: {indicator}")
    
    client = IMFClient()
    
    try:
        endpoint = f'/{indicator}'
        
        if countries:
            country_str = ','.join(countries)
            endpoint += f'/{country_str}'
        
        response = client.get_json(endpoint)
        
        if 'values' not in response:
            logger.warning(f"No data returned for indicator {indicator}")
            return pd.DataFrame()
        
        records = []
        for country_code, data in response['values'].items():
            for year, value in data.items():
                year_int = int(year)
                
                # Filter by date range
                if start_year and year_int < start_year:
                    continue
                if end_year and year_int > end_year:
                    continue
                
                if value and value != '':
                    records.append({
                        'country_code': country_code,
                        'year': year_int,
                        'value': float(value),
                        'indicator': indicator,
                    })
        
        df = pd.DataFrame(records)
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['year'].astype(str) + '-12-31')
        
        logger.info(f"Fetched {len(df)} records for IMF indicator {indicator}")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching IMF indicator {indicator}: {e}")
        raise
    finally:
        client.close()


def fetch_imf_world_economic_outlook() -> pd.DataFrame:
    """
    Fetch World Economic Outlook data from IMF.
    
    Returns:
        DataFrame with WEO projections and historical data
    """
    logger.info("Fetching IMF World Economic Outlook data")
    
    client = IMFClient()
    
    try:
        # Common WEO indicators
        indicators = [
            'NGDP_RPCH',  # GDP growth
            'PCPIPCH',    # Inflation
            'LUR',        # Unemployment
            'GGX_NGDP',   # Government expenditure
        ]
        
        all_data = []
        
        for indicator in indicators:
            try:
                df = fetch_imf_indicator(indicator)
                if not df.empty:
                    all_data.append(df)
            except Exception as e:
                logger.error(f"Error fetching WEO indicator {indicator}: {e}")
                continue
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            logger.info(f"Fetched {len(combined_df)} WEO records")
            return combined_df
        
        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Error fetching IMF WEO data: {e}")
        raise
    finally:
        client.close()


def refresh_imf_data(
    include_exchange_rates: bool = True,
    include_weo: bool = True,
    countries: Optional[List[str]] = None
) -> int:
    """
    Refresh IMF data in the database.
    
    This is the main entry point called by schedulers.
    
    Args:
        include_exchange_rates: Whether to fetch exchange rates
        include_weo: Whether to fetch World Economic Outlook data
        countries: List of country codes. If None, uses major economies
        
    Returns:
        Number of records inserted
    """
    from modules.database.queries import insert_generic_data
    
    # Default to major economies
    if countries is None:
        countries = ['US', 'CN', 'JP', 'DE', 'IN', 'GB', 'FR', 'BR', 'IT', 'CA']
    
    total_records = 0
    
    # Fetch exchange rates
    if include_exchange_rates:
        logger.info("Refreshing IMF exchange rates")
        try:
            df = fetch_imf_exchange_rates(countries=countries)
            if not df.empty:
                records = insert_generic_data(df, 'imf_exchange_rates')
                total_records += records
                logger.info(f"Inserted {records} IMF exchange rate records")
        except Exception as e:
            logger.error(f"Error refreshing IMF exchange rates: {e}")
    
    # Fetch WEO data
    if include_weo:
        logger.info("Refreshing IMF World Economic Outlook data")
        try:
            df = fetch_imf_world_economic_outlook()
            if not df.empty:
                records = insert_generic_data(df, 'imf_indicators')
                total_records += records
                logger.info(f"Inserted {records} IMF WEO records")
        except Exception as e:
            logger.error(f"Error refreshing IMF WEO data: {e}")
    
    logger.info(f"Total IMF records inserted: {total_records}")
    return total_records
