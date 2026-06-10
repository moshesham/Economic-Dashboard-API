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
import re

logger = logging.getLogger(__name__)


# Full Economic Indicator Time Series (EITS) datasets supported by this loader.
CENSUS_EITS_DATASETS = {
    'advm3': {'endpoint': '/timeseries/eits/advm3', 'indicator': 'ADV_DURABLE_GOODS'},
    'bfs': {'endpoint': '/timeseries/eits/bfs', 'indicator': 'BUSINESS_FORMATION'},
    'ftd': {'endpoint': '/timeseries/eits/ftd', 'indicator': 'INTL_TRADE_GOODS_SERVICES'},
    'hv': {'endpoint': '/timeseries/eits/hv', 'indicator': 'HOUSING_VACANCIES_HOMEOWNERSHIP'},
    'm3': {'endpoint': '/timeseries/eits/m3', 'indicator': 'MFG_SHIP_INV_ORDERS'},
    'marts': {'endpoint': '/timeseries/eits/marts', 'indicator': 'RETAIL_SALES_ADVANCE'},
    'mhs': {'endpoint': '/timeseries/eits/mhs', 'indicator': 'MANUFACTURED_HOMES_SURVEY'},
    'mhs2': {'endpoint': '/timeseries/eits/mhs2', 'indicator': 'MANUFACTURED_HOUSING_2014P'},
    'mrts': {'endpoint': '/timeseries/eits/mrts', 'indicator': 'MONTHLY_RETAIL_TRADE'},
    'mtis': {'endpoint': '/timeseries/eits/mtis', 'indicator': 'MFG_TRADE_INV_SALES'},
    'mwts': {'endpoint': '/timeseries/eits/mwts', 'indicator': 'MONTHLY_WHOLESALE_TRADE'},
    'qfr': {'endpoint': '/timeseries/eits/qfr', 'indicator': 'QUARTERLY_FINANCIAL_REPORT'},
    'qpr': {'endpoint': '/timeseries/eits/qpr', 'indicator': 'PUBLIC_PENSIONS_QTR'},
    'qss': {'endpoint': '/timeseries/eits/qss', 'indicator': 'QUARTERLY_SERVICES_SURVEY'},
    'qtax': {'endpoint': '/timeseries/eits/qtax', 'indicator': 'STATE_LOCAL_TAX_QTR'},
    'resconst': {'endpoint': '/timeseries/eits/resconst', 'indicator': 'NEW_RESIDENTIAL_CONSTRUCTION'},
    'ressales': {'endpoint': '/timeseries/eits/ressales', 'indicator': 'NEW_HOME_SALES'},
    'vip': {'endpoint': '/timeseries/eits/vip', 'indicator': 'CONSTRUCTION_SPENDING'},
}

# Backward-compatible alias retained for existing call sites.
CENSUS_DATASETS = {
    meta['endpoint'].lstrip('/'): meta['indicator']
    for meta in CENSUS_EITS_DATASETS.values()
}


class CensusBureauDataLoader:
    """
    A unified loader to fetch economic, construction, and international trade 
    data from the US Census Bureau API.
    """

    def __init__(self, api_key: Optional[str] = None):
        # Resolve Census API key
        self.api_key = self._normalize_api_key(api_key or os.getenv('CENSUS_API_KEY'))
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

    @staticmethod
    def _normalize_api_key(raw_key: Optional[str]) -> Optional[str]:
        """Normalize optional API key and treat template placeholders as missing."""
        if not raw_key:
            return None

        key = str(raw_key).strip()
        if not key:
            return None

        placeholders = {
            'your_census_api_key_here',
            'your_api_key_here',
            'changeme',
            'change-me',
        }
        if key.lower() in placeholders:
            return None

        return key

    @staticmethod
    def _parse_time_to_date(raw_time: Any, raw_slot: Any = None) -> Optional[str]:
        """Parse multiple Census time representations into an ISO date string."""
        if raw_time is not None:
            time_str = str(raw_time).strip()
            if re.match(r'^\d{4}-\d{2}$', time_str):
                return f"{time_str}-01"
            if re.match(r'^\d{4}$', time_str):
                return f"{time_str}-01-01"
            q_match = re.match(r'^(\d{4})-Q([1-4])$', time_str)
            if q_match:
                year = int(q_match.group(1))
                quarter = int(q_match.group(2))
                month = (quarter - 1) * 3 + 1
                return f"{year}-{month:02d}-01"

        if raw_slot is not None:
            slot = str(raw_slot).strip()
            if len(slot) == 6 and slot.isdigit():
                year = int(slot[:4])
                month = int(slot[4:6])
                if 1 <= month <= 12:
                    return f"{year}-{month:02d}-01"
            if len(slot) == 4 and slot.isdigit():
                return f"{slot}-01-01"

        return None

    @staticmethod
    def _build_category(row: Dict[str, Any]) -> str:
        """Create a stable category that also captures geography when present."""
        base_category = str(row.get('category_code', '') or row.get('data_type_code', '')).strip()
        geo_parts: List[str] = []
        seasonality_raw = str(row.get('seasonally_adj', '') or '').strip().lower()

        for geo_col in ('us', 'region', 'division', 'state', 'county', 'place'):
            geo_val = row.get(geo_col)
            if geo_val is not None and str(geo_val).strip() != '':
                geo_parts.append(f"{geo_col}={str(geo_val).strip()}")

        if geo_parts:
            geo_token = '|'.join(geo_parts)
            base_category = f"{base_category}|{geo_token}" if base_category else geo_token

        # Keep SA/NSA variants distinct to match the table's uniqueness constraints.
        if seasonality_raw in ('yes', 'no'):
            sa_token = 'sa' if seasonality_raw == 'yes' else 'nsa'
            return f"{base_category}|{sa_token}" if base_category else sa_token

        return base_category

    def _request_eits(self, endpoint: str, start_year: int) -> List[List[Any]]:
        """Request EITS data with fallback geography parameters for strict endpoints."""
        base_params = {
            'get': 'cell_value,data_type_code,time_slot_id,category_code,seasonally_adj',
            'time': f'from {start_year}',
        }
        attempts = [
            base_params,
            {**base_params, 'for': 'us:*'},
            {**base_params, 'for': 'us:1'},
            {**base_params, 'for': 'us:*', 'NAICS2017': '*'},
            {**base_params, 'for': 'us:1', 'NAICS2017': '*'},
        ]

        last_error: Optional[Exception] = None
        for params in attempts:
            try:
                response = self.client.get_json(endpoint, params=params)
            except Exception as exc:
                last_error = exc
                continue

            if isinstance(response, list) and len(response) >= 2:
                return response

        if last_error:
            raise last_error
        return []

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
        response = self._request_eits(endpoint, start_year)

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
                
                category = self._build_category(row)
                seasonally_adj = row.get('seasonally_adj', '')

                # Extract and parse the standard date from 'time' or fallback to 'time_slot_id'
                date_str = self._parse_time_to_date(
                    raw_time=row.get('time') or row.get('time_period'),
                    raw_slot=row.get('time_slot_id')
                )

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

    def fetch_eits_dataset(self, dataset_key: str, start_year: int) -> pd.DataFrame:
        """Fetch a supported EITS dataset and annotate with a standardized indicator."""
        ds_key = dataset_key.strip().lower()
        if ds_key not in CENSUS_EITS_DATASETS:
            raise ValueError(f"Unsupported Census EITS dataset: {dataset_key}")

        meta = CENSUS_EITS_DATASETS[ds_key]
        df = self.fetch_eits_data(meta['endpoint'], start_year)
        if not df.empty:
            df['indicator'] = meta['indicator']
        return df

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
        df = loader.fetch_eits_dataset('marts', start_year)
        if not df.empty:
            # Preserve legacy indicator expected by existing pages/tests.
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
        df = loader.fetch_eits_dataset('resconst', start_year)
        if not df.empty:
            # Preserve legacy indicator expected by existing pages/tests.
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
    api_key: Optional[str] = None,
    datasets: Optional[List[str]] = None,
    start_year: Optional[int] = None,
) -> int:
    """
    Refresh Census Bureau data in the database.
    """
    from modules.database.queries import insert_generic_data
    
    total_records = 0
    if start_year is None:
        start_year = datetime.now().year - 5

    if datasets:
        dataset_list = [d.strip().lower() for d in datasets]
        logger.info(f"Refreshing Census EITS datasets: {dataset_list}")
        loader = CensusBureauDataLoader(api_key=api_key)
        try:
            for ds_key in dataset_list:
                try:
                    df = loader.fetch_eits_dataset(ds_key, start_year=start_year)
                    if not df.empty:
                        df = df.drop_duplicates(subset=['date', 'indicator', 'category'], keep='last')
                        records = insert_generic_data(df, 'census_data')
                        total_records += records
                        logger.info(f"Inserted {records} Census records for dataset={ds_key}")
                    else:
                        logger.info(f"No Census records returned for dataset={ds_key}")
                except Exception as e:
                    logger.error(f"Error refreshing Census dataset={ds_key}: {e}")
        finally:
            loader.close()

        logger.info(f"Total Census records inserted: {total_records}")
        return total_records
    
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
