"""
Data Source Configuration Framework

Centralized configuration for all data sources with SLA-aware refresh logic.
Provides a declarative way to add new data sources to the system.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, Any, List
from datetime import timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DataFrequency(str, Enum):
    """Data update frequency categories."""
    REALTIME = "realtime"  # Continuous updates
    INTRADAY = "intraday"  # Multiple times per day
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class DataSourceType(str, Enum):
    """Type of data source."""
    API = "api"  # REST API
    FILE_DOWNLOAD = "file_download"  # CSV/Excel downloads
    WEB_SCRAPE = "web_scrape"  # Web scraping
    DATABASE = "database"  # Direct database connection
    STREAM = "stream"  # Real-time stream


@dataclass
class DataSourceConfig:
    """
    Configuration for a data source.
    
    This defines everything needed to fetch, validate, and store data
    from a particular source.
    """
    
    # Identity
    source_id: str  # Unique identifier (e.g., 'fred_gdp', 'yf_spy')
    source_name: str  # Human-readable name
    source_type: DataSourceType
    
    # Data characteristics
    frequency: DataFrequency
    sla: timedelta  # Service Level Agreement - max data staleness
    
    # Storage configuration
    table_name: str  # Database table to store data
    validation_type: str  # Validation schema type
    
    # Fetch configuration
    fetch_function: Callable  # Function to fetch the data
    fetch_params: Dict[str, Any] = field(default_factory=dict)
    
    # API configuration (if applicable)
    requires_api_key: bool = False
    api_key_env_var: Optional[str] = None
    rate_limit: Optional[tuple] = None  # (max_calls, period_seconds)
    
    # Schedule configuration
    cron_schedule: Optional[str] = None  # Cron expression for scheduling
    enabled: bool = True
    
    # Metadata
    description: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)  # Other sources this depends on
    tags: List[str] = field(default_factory=list)
    
    def is_stale(self, last_update: Optional[Any]) -> bool:
        """
        Check if data is stale based on SLA.
        
        Args:
            last_update: Datetime of last update
            
        Returns:
            True if data needs refresh
        """
        if last_update is None:
            return True
        
        from datetime import datetime
        if isinstance(last_update, str):
            from dateutil import parser
            last_update = parser.parse(last_update)
        
        age = datetime.utcnow() - last_update
        return age > self.sla
    
    def can_fetch_now(self) -> bool:
        """
        Check if data can be fetched now based on frequency.
        
        For example, monthly data shouldn't be fetched mid-month.
        """
        from datetime import datetime
        now = datetime.utcnow()
        
        if self.frequency == DataFrequency.MONTHLY:
            # Only fetch on first 5 days of month
            return now.day <= 5
        elif self.frequency == DataFrequency.QUARTERLY:
            # Only fetch in first month of quarter
            return now.month % 3 == 1 and now.day <= 5
        
        return True


# ============================================================================
# DATA SOURCE REGISTRY
# ============================================================================

class DataSourceRegistry:
    """
    Registry of all configured data sources.
    
    Provides methods to register, retrieve, and manage data sources.
    """
    
    def __init__(self):
        self._sources: Dict[str, DataSourceConfig] = {}
    
    def register(self, config: DataSourceConfig):
        """Register a data source configuration."""
        if config.source_id in self._sources:
            logger.warning(f"Overwriting existing source: {config.source_id}")
        
        self._sources[config.source_id] = config
        logger.info(f"Registered data source: {config.source_id}")
    
    def get(self, source_id: str) -> DataSourceConfig:
        """Get a data source configuration by ID."""
        if source_id not in self._sources:
            raise ValueError(f"Unknown data source: {source_id}")
        return self._sources[source_id]
    
    def list_all(self) -> List[DataSourceConfig]:
        """Get all registered data sources."""
        return list(self._sources.values())
    
    def list_by_frequency(self, frequency: DataFrequency) -> List[DataSourceConfig]:
        """Get all sources with a specific frequency."""
        return [s for s in self._sources.values() if s.frequency == frequency]
    
    def list_enabled(self) -> List[DataSourceConfig]:
        """Get all enabled data sources."""
        return [s for s in self._sources.values() if s.enabled]
    
    def list_by_tag(self, tag: str) -> List[DataSourceConfig]:
        """Get all sources with a specific tag."""
        return [s for s in self._sources.values() if tag in s.tags]


# Global registry instance
_registry = DataSourceRegistry()


def register_source(config: DataSourceConfig):
    """Register a data source in the global registry."""
    _registry.register(config)


def get_source(source_id: str) -> DataSourceConfig:
    """Get a data source from the global registry."""
    return _registry.get(source_id)


def list_sources(**filters) -> List[DataSourceConfig]:
    """
    List data sources with optional filters.
    
    Args:
        frequency: Filter by frequency
        enabled: Filter by enabled status
        tag: Filter by tag
        
    Returns:
        List of matching data source configurations
    """
    if 'frequency' in filters:
        return _registry.list_by_frequency(filters['frequency'])
    elif 'tag' in filters:
        return _registry.list_by_tag(filters['tag'])
    elif 'enabled' in filters:
        if filters['enabled']:
            return _registry.list_enabled()
    
    return _registry.list_all()


# ============================================================================
# EXAMPLE DATA SOURCE CONFIGURATIONS
# ============================================================================

def register_default_sources():
    """Register default data sources."""
    
    # FRED GDP
    register_source(DataSourceConfig(
        source_id='fred_gdp',
        source_name='US Real GDP',
        source_type=DataSourceType.API,
        frequency=DataFrequency.QUARTERLY,
        sla=timedelta(days=30),
        fetch_function='modules.data_loader.fetch_fred_series',
        fetch_params={'series_id': 'GDPC1'},
        table_name='fred_data',
        validation_type='fred',
        requires_api_key=True,
        api_key_env_var='FRED_API_KEY',
        rate_limit=(120, 60),
        cron_schedule='0 6 1 * *',  # First day of month at 6 AM
        description='US Real Gross Domestic Product',
        tags=['fred', 'macro', 'gdp'],
    ))
    
    # FRED CPI
    register_source(DataSourceConfig(
        source_id='fred_cpi',
        source_name='Consumer Price Index',
        source_type=DataSourceType.API,
        frequency=DataFrequency.MONTHLY,
        sla=timedelta(days=7),
        fetch_function='modules.data_loader.fetch_fred_series',
        fetch_params={'series_id': 'CPIAUCSL'},
        table_name='fred_data',
        validation_type='fred',
        requires_api_key=True,
        api_key_env_var='FRED_API_KEY',
        rate_limit=(120, 60),
        cron_schedule='0 6 15 * *',  # 15th of month at 6 AM
        description='Consumer Price Index for All Urban Consumers',
        tags=['fred', 'macro', 'inflation'],
    ))
    
    # Yahoo Finance - S&P 500
    register_source(DataSourceConfig(
        source_id='yf_spy',
        source_name='S&P 500 ETF (SPY)',
        source_type=DataSourceType.API,
        frequency=DataFrequency.DAILY,
        sla=timedelta(hours=6),
        fetch_function='modules.data_loader.fetch_yfinance_ohlcv',
        fetch_params={'ticker': 'SPY'},
        table_name='yfinance_ohlcv',
        validation_type='stock',
        requires_api_key=False,
        rate_limit=(2000, 3600),
        cron_schedule='0 22 * * 1-5',  # 10 PM weekdays
        description='S&P 500 ETF daily price data',
        tags=['yfinance', 'equity', 'index'],
    ))
    
    # CBOE VIX
    register_source(DataSourceConfig(
        source_id='cboe_vix',
        source_name='CBOE VIX Index',
        source_type=DataSourceType.FILE_DOWNLOAD,
        frequency=DataFrequency.DAILY,
        sla=timedelta(hours=24),
        fetch_function='modules.cboe_vix_data.fetch_vix_history',
        fetch_params={},
        table_name='cboe_vix_history',
        validation_type='cboe_vix',
        requires_api_key=False,
        rate_limit=(60, 60),
        cron_schedule='0 22 * * 1-5',  # 10 PM weekdays
        description='CBOE Volatility Index historical data',
        tags=['cboe', 'volatility', 'vix'],
    ))
    
    # ICI ETF Weekly Flows
    register_source(DataSourceConfig(
        source_id='ici_etf_weekly',
        source_name='ICI ETF Weekly Flows',
        source_type=DataSourceType.FILE_DOWNLOAD,
        frequency=DataFrequency.WEEKLY,
        sla=timedelta(days=1),
        fetch_function='modules.ici_etf_data.fetch_weekly_flows',
        fetch_params={},
        table_name='ici_etf_weekly_flows',
        validation_type='ici_weekly',
        requires_api_key=False,
        rate_limit=(30, 60),
        cron_schedule='0 8 * * 3',  # Wednesday at 8 AM
        description='Investment Company Institute weekly ETF flow statistics',
        tags=['ici', 'etf', 'flows'],
    ))
    
    logger.info("Default data sources registered")


# Initialize default sources on module import
register_default_sources()
