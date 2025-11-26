"""
Data loading module for Economic Dashboard.
Handles all data fetching from FRED and Yahoo Finance with caching and offline support.
"""

import streamlit as st
import pandas as pd
import yfinance as yf
from pandas_datareader import data as pdr
from datetime import datetime, timedelta
import os
import pickle
import time
from config_settings import (
    is_offline_mode, can_use_offline_data, get_cache_dir,
    ensure_cache_dir, CACHE_EXPIRY_HOURS, YFINANCE_RATE_LIMIT_DELAY,
    YFINANCE_BATCH_SIZE, YFINANCE_CACHE_HOURS
)
from modules.auth.credentials_manager import get_credentials_manager


# Configure proxy if available (for GitHub Actions IP rotation)
def _setup_proxy():
    """Configure proxy settings from environment variables."""
    proxy_url = os.environ.get('PROXY_URL')
    if proxy_url:
        # Set yfinance session with proxy
        import requests
        session = requests.Session()
        session.proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        # Note: yfinance doesn't easily support custom sessions,
        # but this sets up the environment for requests-based calls
        os.environ['HTTP_PROXY'] = proxy_url
        os.environ['HTTPS_PROXY'] = proxy_url
        return True
    return False

# Initialize proxy on module load
_PROXY_ENABLED = _setup_proxy()


def _load_cached_data(cache_file: str, max_age_hours: int | None = None) -> pd.DataFrame | dict | None:
    """Load data from cache if it exists and is not expired.
    
    Args:
        cache_file: Path to cache file
        max_age_hours: Maximum age in hours before cache is considered stale.
                      If None, uses CACHE_EXPIRY_HOURS
    """
    if not os.path.exists(cache_file):
        return None

    try:
        with open(cache_file, 'rb') as f:
            cache_data = pickle.load(f)

        # Check if cache is expired
        cache_time = cache_data['timestamp']
        expiry_hours = max_age_hours if max_age_hours is not None else CACHE_EXPIRY_HOURS
        if datetime.now() - cache_time > timedelta(hours=expiry_hours):
            return None

        return cache_data['data']
    except Exception:
        return None


def _save_cached_data(cache_file: str, data):
    """Save data to cache."""
    ensure_cache_dir()
    cache_data = {
        'timestamp': datetime.now(),
        'data': data
    }

    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(cache_data, f)
    except Exception as e:
        st.warning(f"Could not save cache: {e}")


def _load_offline_fred_data(series_ids: dict) -> pd.DataFrame:
    """Load FRED data from offline sample file."""
    try:
        if not can_use_offline_data('fred'):
            st.warning("Offline FRED data not available")
            return pd.DataFrame()

        df = pd.read_csv('data/sample_fred_data.csv', index_col=0, parse_dates=True)

        # Filter to requested series
        available_series = [sid for sid in series_ids.values() if sid in df.columns]
        if not available_series:
            st.warning("Requested FRED series not available in offline data")
            return pd.DataFrame()

        result_df = df[available_series].copy()
        # Rename columns back to descriptive names
        reverse_mapping = {v: k for k, v in series_ids.items()}
        result_df = result_df.rename(columns=reverse_mapping)

        return result_df
    except Exception as e:
        st.error(f"Error loading offline FRED data: {e}")
        return pd.DataFrame()


def _load_offline_yfinance_data(tickers: dict, period: str = "5y") -> dict:
    """Load Yahoo Finance data from offline sample files."""
    try:
        if not can_use_offline_data('yfinance'):
            st.warning("Offline Yahoo Finance data not available")
            return {}

        result = {}
        for name, ticker in tickers.items():
            filename = f"data/sample_{ticker.replace('^', '')}_data.csv"
            if os.path.exists(filename):
                df = pd.read_csv(filename, index_col=0, parse_dates=True)
                result[name] = df
            else:
                st.warning(f"Offline data for {ticker} not available")

        return result
    except Exception as e:
        st.error(f"Error loading offline Yahoo Finance data: {e}")
        return {}


@st.cache_data(ttl=3600)
def load_fred_data(series_ids: dict) -> pd.DataFrame:
    """
    Load economic data from FRED database.

    Args:
        series_ids: Dictionary with descriptive names as keys and FRED series IDs as values

    Returns:
        DataFrame with DatetimeIndex and columns for each series
    """
    # Check offline mode first
    if is_offline_mode():
        return _load_offline_fred_data(series_ids)

    # First, try to load from the centralized cache (updated daily by automation)
    centralized_cache = f"{get_cache_dir()}/fred_all_series.pkl"
    if os.path.exists(centralized_cache):
        try:
            cached_data = _load_cached_data(centralized_cache)
            if cached_data is not None and isinstance(cached_data, pd.DataFrame):
                # Filter to requested series
                available_series = [name for name in series_ids.keys() if name in cached_data.columns]
                if available_series:
                    return cached_data[available_series].copy()
        except Exception as e:
            st.warning(f"Could not load from centralized cache: {e}")

    # Fallback: Try to load from individual cache
    cache_key = str(sorted(series_ids.items()))
    cache_file = f"{get_cache_dir()}/fred_{hash(cache_key)}.pkl"
    cached_data = _load_cached_data(cache_file)
    if cached_data is not None and isinstance(cached_data, pd.DataFrame):
        return cached_data

    # Load from API
    try:
        # Get FRED API key from credentials manager
        creds_manager = get_credentials_manager()
        fred_api_key = creds_manager.get_api_key('fred')
        
        data_frames = {}
        for name, series_id in series_ids.items():
            try:
                # Use API key if available
                if fred_api_key:
                    df = pdr.DataReader(series_id, 'fred', start='2000-01-01', api_key=fred_api_key)
                else:
                    # Fallback to unauthenticated access
                    df = pdr.DataReader(series_id, 'fred', start='2000-01-01')
                
                if not df.empty:
                    data_frames[name] = df.iloc[:, 0]
            except Exception as e:
                st.warning(f"Could not load {name} ({series_id}): {str(e)}")
                continue

        if data_frames:
            result = pd.DataFrame(data_frames)
            # Save to cache
            _save_cached_data(cache_file, result)
            return result
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading FRED data: {str(e)}")
        # Fallback to offline data if available
        if can_use_offline_data('fred'):
            st.info("Falling back to offline data")
            return _load_offline_fred_data(series_ids)
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_yfinance_data(tickers: dict, period: str = "5y") -> dict:
    """
    Load market data from Yahoo Finance with rate limiting and smart caching.

    Args:
        tickers: Dictionary with descriptive names as keys and ticker symbols as values
        period: Time period to fetch (e.g., '1y', '5y', '10y')

    Returns:
        Dictionary of DataFrames, one for each ticker
    """
    # Check offline mode first
    if is_offline_mode():
        return _load_offline_yfinance_data(tickers, period)

    # First, try to load from the centralized cache (updated daily by automation)
    centralized_cache = f"{get_cache_dir()}/yfinance_all_tickers.pkl"
    if os.path.exists(centralized_cache):
        try:
            cached_data = _load_cached_data(centralized_cache, max_age_hours=YFINANCE_CACHE_HOURS)
            if cached_data is not None and isinstance(cached_data, dict):
                # Filter to requested tickers
                available_tickers = {name: data for name, data in cached_data.items() if name in tickers.keys()}
                if available_tickers:
                    return available_tickers
        except Exception as e:
            st.warning(f"Could not load from centralized cache: {e}")

    # Fallback: Try to load from individual cache with 24-hour expiry
    cache_key = str(sorted(tickers.items())) + period
    cache_file = f"{get_cache_dir()}/yfinance_{hash(cache_key)}.pkl"
    cached_data = _load_cached_data(cache_file, max_age_hours=YFINANCE_CACHE_HOURS)
    if cached_data is not None and isinstance(cached_data, dict):
        # Check if we have all requested tickers in cache
        if all(name in cached_data for name in tickers.keys()):
            return cached_data

    # Load from API with rate limiting
    try:
        result = {}
        ticker_list = list(tickers.items())
        total_tickers = len(ticker_list)
        
        # Process in batches to avoid rate limiting
        for i in range(0, total_tickers, YFINANCE_BATCH_SIZE):
            batch = ticker_list[i:i + YFINANCE_BATCH_SIZE]
            
            for name, ticker in batch:
                try:
                    # Add delay between requests to respect rate limits
                    if i > 0 or result:  # Don't delay on first request
                        time.sleep(YFINANCE_RATE_LIMIT_DELAY)
                    
                    # Download with auto_adjust=True to avoid FutureWarning
                    data = yf.download(ticker, period=period, progress=False, auto_adjust=True)
                    
                    if data is not None and not data.empty:
                        # Handle MultiIndex columns for single ticker
                        if isinstance(data.columns, pd.MultiIndex):
                            data.columns = data.columns.get_level_values(0)
                        result[name] = data
                    else:
                        st.warning(f"No data available for {name} ({ticker})")
                except Exception as e:
                    error_msg = str(e)
                    # Provide more specific error messages
                    if "Rate limit" in error_msg or "Too Many Requests" in error_msg:
                        st.warning(f"⏱️ Rate limited on {name} ({ticker}). Using cached data if available.")
                        # Try to load from any available cache, even if expired
                        old_cached = _load_cached_data(cache_file, max_age_hours=168)  # 1 week
                        if old_cached is not None and isinstance(old_cached, dict) and name in old_cached:
                            result[name] = old_cached[name]
                            st.info(f"Using cached data for {name} (may be up to 1 week old)")
                    elif "No objects to concatenate" in error_msg:
                        st.warning(f"Could not load {name} ({ticker}): Data not available for this period")
                    else:
                        st.warning(f"Could not load {name} ({ticker}): {error_msg}")
                    continue

        if result:
            # Save to cache with current timestamp
            _save_cached_data(cache_file, result)

        return result
    except Exception as e:
        st.error(f"Error loading Yahoo Finance data: {str(e)}")
        # Fallback to offline data if available
        if can_use_offline_data('yfinance'):
            st.info("Falling back to offline data")
            return _load_offline_yfinance_data(tickers, period)
        return {}


@st.cache_data(ttl=3600)
def get_yield_curve_data() -> pd.DataFrame:
    """
    Fetch US Treasury yield data and calculate spread.
    
    Returns:
        DataFrame with 10-Year yield, 2-Year yield, and spread
    """
    try:
        series_ids = {
            '10-Year': 'DGS10',
            '2-Year': 'DGS2'
        }
        
        df = load_fred_data(series_ids)
        
        if not df.empty and '10-Year' in df.columns and '2-Year' in df.columns:
            df['Spread'] = df['10-Year'] - df['2-Year']
            return df.dropna()
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error calculating yield curve: {str(e)}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_world_bank_gdp() -> pd.DataFrame:
    """
    Load World Bank GDP growth data.
    Note: This is a simplified version. For production, use World Bank API.

    Returns:
        DataFrame with GDP growth by country
    """
    # Check offline mode first
    if is_offline_mode():
        try:
            if not can_use_offline_data('world_bank'):
                st.warning("Offline World Bank data not available")
                return pd.DataFrame()

            df = pd.read_csv('data/sample_world_bank_gdp.csv')
            return df
        except Exception as e:
            st.error(f"Error loading offline World Bank data: {e}")
            return pd.DataFrame()

    # Try to load from cache
    cache_file = f"{get_cache_dir()}/world_bank_gdp.pkl"
    cached_data = _load_cached_data(cache_file)
    if cached_data is not None and isinstance(cached_data, pd.DataFrame):
        return cached_data

    # Load from API (simplified version)
    try:
        # For now, return a simple dataset
        # In production, integrate with World Bank API or use a CSV file
        countries = ['United States', 'China', 'Germany', 'Japan', 'United Kingdom',
                     'France', 'India', 'Brazil', 'Canada', 'South Korea']
        gdp_growth = [2.1, 5.2, 0.9, 1.0, 1.3, 1.1, 6.8, 1.2, 1.5, 2.6]

        df = pd.DataFrame({
            'Country': countries,
            'GDP Growth (%)': gdp_growth,
            'ISO3': ['USA', 'CHN', 'DEU', 'JPN', 'GBR', 'FRA', 'IND', 'BRA', 'CAN', 'KOR']
        })

        # Save to cache
        _save_cached_data(cache_file, df)

        return df
    except Exception as e:
        st.error(f"Error loading World Bank data: {str(e)}")
        # Fallback to offline data if available
        if can_use_offline_data('world_bank'):
            st.info("Falling back to offline data")
            try:
                df = pd.read_csv('data/sample_world_bank_gdp.csv')
                return df
            except Exception:
                return pd.DataFrame()
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def get_latest_value(series_id: str) -> float | None:
    """
    Get the most recent value for a FRED series.

    Args:
        series_id: FRED series ID

    Returns:
        Latest value as float
    """
    # Check offline mode first
    if is_offline_mode():
        try:
            if not can_use_offline_data('fred'):
                st.warning("Offline FRED data not available")
                return None

            df = pd.read_csv('data/sample_fred_data.csv', index_col=0, parse_dates=True)
            if series_id in df.columns and not df[series_id].empty:
                return float(df[series_id].iloc[-1])
            return None
        except Exception as e:
            st.error(f"Error loading offline FRED data: {e}")
            return None

    # Try to load from cache
    cache_file = f"{get_cache_dir()}/fred_latest_{series_id}.pkl"
    cached_data = _load_cached_data(cache_file)
    if cached_data is not None and isinstance(cached_data, (int, float)):
        return float(cached_data)

    # Load from API
    try:
        # Get FRED API key from credentials manager
        creds_manager = get_credentials_manager()
        fred_api_key = creds_manager.get_api_key('fred')
        
        # Use API key if available
        if fred_api_key:
            df = pdr.DataReader(series_id, 'fred', start=(datetime.now() - timedelta(days=365)), api_key=fred_api_key)
        else:
            df = pdr.DataReader(series_id, 'fred', start=(datetime.now() - timedelta(days=365)))
        
        if not df.empty:
            latest_value = float(df.iloc[-1, 0])
            # Save to cache
            _save_cached_data(cache_file, latest_value)
            return latest_value
        return None
    except Exception as e:
        st.warning(f"Could not fetch latest value for {series_id}: {str(e)}")
        # Fallback to offline data
        if can_use_offline_data('fred'):
            st.info("Falling back to offline data")
            try:
                df = pd.read_csv('data/sample_fred_data.csv', index_col=0, parse_dates=True)
                if series_id in df.columns and not df[series_id].empty:
                    return float(df[series_id].iloc[-1])
            except Exception:
                pass
        return None


@st.cache_data(ttl=3600)
def calculate_yoy_change(series_id: str) -> float | None:
    """
    Calculate year-over-year percentage change (12-month change for monthly data).

    Args:
        series_id: FRED series ID

    Returns:
        Year-over-year percentage change as float
    """
    return calculate_percentage_change(series_id, periods=12)


@st.cache_data(ttl=3600)
def calculate_percentage_change(series_id: str, periods: int = 4) -> float | None:
    """
    Calculate percentage change over specified periods.

    Args:
        series_id: FRED series ID
        periods: Number of periods to look back

    Returns:
        Percentage change as float
    """
    # Check offline mode first
    if is_offline_mode():
        try:
            if not can_use_offline_data('fred'):
                st.warning("Offline FRED data not available")
                return None

            df = pd.read_csv('data/sample_fred_data.csv', index_col=0, parse_dates=True)
            if series_id in df.columns and len(df) >= periods + 1:
                latest = df[series_id].iloc[-1]
                previous = df[series_id].iloc[-(periods + 1)]
                return ((latest - previous) / previous) * 100
            return None
        except Exception as e:
            st.error(f"Error loading offline FRED data: {e}")
            return None

    # Try to load from cache
    cache_file = f"{get_cache_dir()}/fred_change_{series_id}_{periods}.pkl"
    cached_data = _load_cached_data(cache_file)
    if cached_data is not None and isinstance(cached_data, (int, float)):
        return float(cached_data)

    # Load from API
    try:
        # Get FRED API key from credentials manager
        creds_manager = get_credentials_manager()
        fred_api_key = creds_manager.get_api_key('fred')
        
        # Use API key if available
        if fred_api_key:
            df = pdr.DataReader(series_id, 'fred', start=(datetime.now() - timedelta(days=730)), api_key=fred_api_key)
        else:
            df = pdr.DataReader(series_id, 'fred', start=(datetime.now() - timedelta(days=730)))
        
        if not df.empty and len(df) >= periods + 1:
            latest = df.iloc[-1, 0]
            previous = df.iloc[-(periods + 1), 0]
            change = ((latest - previous) / previous) * 100
            # Save to cache
            _save_cached_data(cache_file, change)
            return change
        return None
    except Exception as e:
        st.warning(f"Could not calculate change for {series_id}: {str(e)}")
        # Fallback to offline data
        if can_use_offline_data('fred'):
            st.info("Falling back to offline data")
            try:
                df = pd.read_csv('data/sample_fred_data.csv', index_col=0, parse_dates=True)
                if series_id in df.columns and len(df) >= periods + 1:
                    latest = df[series_id].iloc[-1]
                    previous = df[series_id].iloc[-(periods + 1)]
                    return ((latest - previous) / previous) * 100
            except Exception:
                pass
        return None
