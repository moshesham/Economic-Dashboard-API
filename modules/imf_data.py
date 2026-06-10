"""
IMF (International Monetary Fund) Data Loader

Fetches economic and financial data from the modern IMF SDMX API via the sdmx1 library.

Based on official SDMX 3.0 guidelines, IMF has reorganized its data:
- Exchange rates are now queried via the 'ER' dataset (COUNTRY.INDICATOR.TRANSFORMATION.FREQUENCY).
- World Economic Outlook projections are queried via the 'WEO' dataset (COUNTRY.INDICATOR.FREQUENCY).
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
import sdmx

logger = logging.getLogger(__name__)

# Mapping to support legacy queries and convert country codes to ISO-3
ISO2_TO_ISO3 = {
    'US': 'USA', 'CN': 'CHN', 'JP': 'JPN', 'DE': 'DEU', 'IN': 'IND',
    'GB': 'GBR', 'FR': 'FRA', 'BR': 'BRA', 'IT': 'ITA', 'CA': 'CAN',
    'TH': 'THA', 'VN': 'VNM', 'CL': 'CHL', 'CO': 'COL', 'SE': 'SWE',
    'MX': 'MEX', 'ES': 'ESP', 'NL': 'NLD', 'RU': 'RUS', 'AU': 'AUS',
    'ZA': 'ZAF', 'KR': 'KOR', 'SA': 'SAU', 'TR': 'TUR', 'CH': 'CHE',
}
ISO3_TO_ISO2 = {v: k for k, v in ISO2_TO_ISO3.items()}


def to_iso3(country: str) -> str:
    """Convert an ISO-2 country code to ISO-3 if found, otherwise keep as is."""
    clean_country = country.strip().upper()
    if len(clean_country) == 2:
        return ISO2_TO_ISO3.get(clean_country, clean_country)
    return clean_country


def find_column_by_names(columns: List[str], candidates: List[str]) -> Optional[str]:
    """Helper to find the active column name in the SDMX output regardless of case."""
    for cand in candidates:
        if cand in columns:
            return cand
        for col in columns:
            if col.upper() == cand.upper():
                return col
    return None


class IMFSDMXDataLoader:
    """
    A unified client for accessing the IMF SDMX API (IMF_DATA).
    Provides automatic conversion for parameters and safely parses SDMX responses.
    """

    def __init__(self):
        # IMF_DATA is the endpoint representing api.imf.org (SDMX 2.1 XML / 3.0 JSON)
        try:
            self.client = sdmx.Client('IMF_DATA')
        except Exception as e:
            logger.error(f"Failed to initialize sdmx.Client for IMF_DATA: {e}")
            raise

    def fetch_raw(
        self,
        dataset_id: str,
        key: str,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Executes a native SDMX query and returns a flat, index-reset pandas DataFrame.
        """
        params = {}
        if start_year:
            params['startPeriod'] = str(start_year)
        if end_year:
            params['endPeriod'] = str(end_year)

        logger.debug(f"Querying IMF SDMX dataflow: '{dataset_id}' with key: '{key}'")
        try:
            data_msg = self.client.data(dataset_id, key=key, params=params)
            df = sdmx.to_pandas(data_msg)
            
            if df.empty:
                logger.warning(f"No data returned for dataset '{dataset_id}' with key '{key}'")
                return pd.DataFrame()
            
            # If to_pandas returns a Series, convert it to a DataFrame for safety
            if isinstance(df, pd.Series):
                df = df.to_frame(name='value')
                
            return df.reset_index()
        except Exception as e:
            logger.error(f"SDMX request error for flow '{dataset_id}' using key '{key}': {e}")
            return pd.DataFrame()


# ==========================================
# Standalone Functions & Drop-in Refits
# ==========================================

def fetch_imf_exchange_rates(countries: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Fetch exchange rates from IMF using the new 'ER' (Exchange Rates) dataset.
    
    Args:
        countries: List of country ISO-2 or ISO-3 codes. If None, fetches default major currencies.
        
    Returns:
        DataFrame with exchange rate data mapped to the legacy structure.
    """
    logger.info("Fetching IMF exchange rates via SDMX")
    
    # Standardize country list to ISO-3 codes
    if countries is None:
        countries = ['US', 'CN', 'JP', 'DE', 'IN', 'GB', 'FR', 'BR', 'IT', 'CA']
    
    iso3_countries = [to_iso3(c) for c in countries]
    country_str = "+".join(iso3_countries)
    
    # DSD Format for ER: COUNTRY.INDICATOR.TRANSFORMATION.FREQUENCY
    # Indicator: XDC_USD (domestic currency per USD)
    # Transformation: EOP_RT (End of Period Exchange Rate)
    # Frequency: A (Annual)
    key = f"{country_str}.XDC_USD.EOP_RT.A"
    
    loader = IMFSDMXDataLoader()
    df_raw = loader.fetch_raw(dataset_id='ER', key=key)
    
    if df_raw.empty:
        return pd.DataFrame()
        
    # Dynamically locate structural columns in response
    col_country = find_column_by_names(df_raw.columns, ['COUNTRY', 'REF_AREA', 'REF_AREAS'])
    col_value = find_column_by_names(df_raw.columns, ['value', 'OBS_VALUE'])
    col_time = find_column_by_names(df_raw.columns, ['TIME_PERIOD', 'PERIOD'])
    
    if not col_time or not col_value:
        logger.error("Required dimensions (time or value) missing in SDMX exchange rate response")
        return pd.DataFrame()
        
    records = []
    for _, row in df_raw.iterrows():
        raw_country = row[col_country] if col_country else 'UNKNOWN'
        # Map back to ISO-2 country codes to align with downstream tables
        country_2 = ISO3_TO_ISO2.get(raw_country, raw_country)
        
        raw_time = str(row[col_time])
        try:
            year_int = int(raw_time[:4])
            val_float = float(row[col_value])
        except (ValueError, TypeError):
            continue
            
        records.append({
            'country_code': country_2,
            'year': year_int,
            'exchange_rate': val_float,
            'indicator': 'ENDA_XDC_USD_RATE',
            'indicator_name': 'Exchange Rate to USD',
        })
        
    df = pd.DataFrame(records)
    if not df.empty:
        df['date'] = pd.to_datetime(df['year'].astype(str) + '-12-31')
        
    logger.info(f"Fetched {len(df)} IMF exchange rate records via SDMX")
    return df


def fetch_imf_indicator(
    indicator: str,
    countries: Optional[List[str]] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None
) -> pd.DataFrame:
    """
    Fetch IMF indicator data. Utilizes WEO dataset as a primary fallback, or ER for FX rates.
    
    Args:
        indicator: IMF indicator code (e.g. 'NGDP_RPCH')
        countries: List of country ISO-2 or ISO-3 codes
        start_year: Start year filter
        end_year: End year filter
        
    Returns:
        DataFrame with indicator data matching legacy schema
    """
    logger.info(f"Fetching IMF indicator: {indicator} via SDMX")
    
    # Resolve target dataset flow
    if indicator in ['ENDA_XDC_USD_RATE', 'XDC_USD']:
        return fetch_imf_exchange_rates(countries)
        
    dataset_id = 'WEO'  # Default for core macroeconomic variables (unemployment, GDP, inflation)
    
    # Standardize country list to ISO-3 codes
    if countries is None:
        countries = ['US', 'CN', 'JP', 'DE', 'IN', 'GB', 'FR', 'BR', 'IT', 'CA']
    
    iso3_countries = [to_iso3(c) for c in countries]
    country_str = "+".join(iso3_countries)
    
    # DSD Format for WEO: COUNTRY.INDICATOR.FREQUENCY
    key = f"{country_str}.{indicator}.A"
    
    loader = IMFSDMXDataLoader()
    df_raw = loader.fetch_raw(dataset_id=dataset_id, key=key, start_year=start_year, end_year=end_year)
    
    if df_raw.empty:
        return pd.DataFrame()
        
    # Locate structural columns in response
    col_country = find_column_by_names(df_raw.columns, ['COUNTRY', 'REF_AREA', 'REF_AREAS'])
    col_value = find_column_by_names(df_raw.columns, ['value', 'OBS_VALUE'])
    col_time = find_column_by_names(df_raw.columns, ['TIME_PERIOD', 'PERIOD'])
    
    if not col_time or not col_value:
        logger.error(f"Required dimensions missing in SDMX response for indicator {indicator}")
        return pd.DataFrame()
        
    records = []
    for _, row in df_raw.iterrows():
        raw_country = row[col_country] if col_country else 'UNKNOWN'
        country_2 = ISO3_TO_ISO2.get(raw_country, raw_country)
        
        raw_time = str(row[col_time])
        try:
            year_int = int(raw_time[:4])
            val_float = float(row[col_value])
        except (ValueError, TypeError):
            continue
            
        records.append({
            'country_code': country_2,
            'year': year_int,
            'value': val_float,
            'indicator': indicator,
        })
        
    df = pd.DataFrame(records)
    if not df.empty:
        df['date'] = pd.to_datetime(df['year'].astype(str) + '-12-31')
        
    logger.info(f"Fetched {len(df)} records for IMF indicator {indicator}")
    return df


def fetch_imf_world_economic_outlook() -> pd.DataFrame:
    """
    Fetch World Economic Outlook data from IMF.
    
    Returns:
        DataFrame with WEO projections and historical data
    """
    logger.info("Fetching IMF World Economic Outlook data")
    
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


def refresh_imf_data(
    include_exchange_rates: bool = True,
    include_weo: bool = True,
    countries: Optional[List[str]] = None
) -> int:
    """
    Refresh IMF data in the database. Preserves legacy scheduler entrypoint structure.
    
    Args:
        include_exchange_rates: Whether to fetch exchange rates
        include_weo: Whether to fetch World Economic Outlook data
        countries: List of country codes
        
    Returns:
        Number of records inserted
    """
    from modules.database.queries import insert_generic_data
    
    # Default to major economies if omitted
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
