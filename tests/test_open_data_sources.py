"""
Tests for Open Data Sources Integration

This test module validates the integration of World Bank, IMF, OECD, BLS, Census, and EIA data sources.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.http_client import (
    WorldBankClient, IMFClient, OECDClient, BLSClient, 
    CensusBureauClient, EIAClient, create_client
)
from modules.validation import (
    WorldBankValidator, IMFExchangeRatesValidator, IMFIndicatorsValidator,
    OECDValidator, BLSValidator, CensusValidator, EIAValidator,
    get_validator
)


class TestHTTPClients:
    """Test HTTP client creation and basic functionality."""
    
    def test_worldbank_client_creation(self):
        """Test World Bank client can be created."""
        client = create_client('worldbank')
        assert isinstance(client, WorldBankClient)
        assert client.base_url == 'https://api.worldbank.org/v2'
    
    def test_imf_client_creation(self):
        """Test IMF client can be created."""
        client = create_client('imf')
        assert isinstance(client, IMFClient)
        assert client.base_url == 'https://www.imf.org/external/datamapper/api/v1'
    
    def test_oecd_client_creation(self):
        """Test OECD client can be created."""
        client = create_client('oecd')
        assert isinstance(client, OECDClient)
        assert client.base_url == 'https://stats.oecd.org/sdmx-json/data'
    
    def test_bls_client_creation(self):
        """Test BLS client can be created with and without API key."""
        # Without API key
        client = create_client('bls')
        assert isinstance(client, BLSClient)
        assert 'v1' in client.base_url
        
        # With API key
        client_with_key = create_client('bls', api_key='test_key')
        assert isinstance(client_with_key, BLSClient)
        assert 'v2' in client_with_key.base_url
    
    def test_census_client_creation(self):
        """Test Census Bureau client requires API key."""
        client = create_client('census', api_key='test_key')
        assert isinstance(client, CensusBureauClient)
        assert client.base_url == 'https://api.census.gov/data'
    
    def test_eia_client_creation(self):
        """Test EIA client requires API key."""
        client = create_client('eia', api_key='test_key')
        assert isinstance(client, EIAClient)
        assert client.base_url == 'https://api.eia.gov/v2'
    
    def test_missing_api_key_raises_error(self):
        """Test that missing API key raises ValueError for clients that require it."""
        with pytest.raises(ValueError, match="requires an API key"):
            create_client('census')
        
        with pytest.raises(ValueError, match="requires an API key"):
            create_client('eia')


class TestValidators:
    """Test data validators for new data sources."""
    
    def test_worldbank_validator(self):
        """Test World Bank validator."""
        validator = get_validator('worldbank')
        assert isinstance(validator, WorldBankValidator)
        
        # Test with valid data
        df = pd.DataFrame({
            'country_code': ['USA', 'CHN'],
            'country_name': ['United States', 'China'],
            'indicator_code': ['NY.GDP.MKTP.CD', 'NY.GDP.MKTP.CD'],
            'indicator_name': ['GDP', 'GDP'],
            'year': [2023, 2023],
            'date': ['2023-12-31', '2023-12-31'],
            'value': [25000.0, 18000.0],
        })
        
        validated_df = validator.validate(df, raise_errors=False)
        assert len(validated_df) == 2
        assert 'date' in validated_df.columns
    
    def test_imf_exchange_rates_validator(self):
        """Test IMF exchange rates validator."""
        validator = get_validator('imf_exchange_rates')
        assert isinstance(validator, IMFExchangeRatesValidator)
        
        df = pd.DataFrame({
            'country_code': ['US', 'CN'],
            'year': [2023, 2023],
            'date': ['2023-12-31', '2023-12-31'],
            'exchange_rate': [1.0, 6.9],
        })
        
        validated_df = validator.validate(df, raise_errors=False)
        assert len(validated_df) == 2
    
    def test_oecd_validator(self):
        """Test OECD validator."""
        validator = get_validator('oecd')
        assert isinstance(validator, OECDValidator)
        
        df = pd.DataFrame({
            'country_code': ['USA', 'JPN'],
            'indicator': ['CLI', 'CLI'],
            'indicator_name': ['Composite Leading Indicator', 'Composite Leading Indicator'],
            'date': ['2023-12-01', '2023-12-01'],
            'value': [100.5, 99.8],
        })
        
        validated_df = validator.validate(df, raise_errors=False)
        assert len(validated_df) == 2
    
    def test_bls_validator(self):
        """Test BLS validator."""
        validator = get_validator('bls')
        assert isinstance(validator, BLSValidator)
        
        df = pd.DataFrame({
            'series_id': ['LNS14000000', 'LNS14000000'],
            'series_name': ['Unemployment Rate', 'Unemployment Rate'],
            'year': [2023, 2023],
            'period': ['M12', 'M11'],
            'date': ['2023-12-01', '2023-11-01'],
            'value': [3.7, 3.9],
        })
        
        validated_df = validator.validate(df, raise_errors=False)
        assert len(validated_df) == 2
    
    def test_census_validator(self):
        """Test Census validator."""
        validator = get_validator('census')
        assert isinstance(validator, CensusValidator)
        
        df = pd.DataFrame({
            'date': ['2023-12-01', '2023-11-01'],
            'indicator': ['RETAIL_SALES', 'RETAIL_SALES'],
            'value': [500000.0, 495000.0],
        })
        
        validated_df = validator.validate(df, raise_errors=False)
        assert len(validated_df) == 2
    
    def test_eia_validator(self):
        """Test EIA validator."""
        validator = get_validator('eia')
        assert isinstance(validator, EIAValidator)
        
        df = pd.DataFrame({
            'series_id': ['PET.RWTC.D', 'PET.RWTC.D'],
            'series_name': ['WTI Crude', 'WTI Crude'],
            'period': ['2023-12-15', '2023-12-14'],
            'date': ['2023-12-15', '2023-12-14'],
            'value': [72.50, 71.80],
        })
        
        validated_df = validator.validate(df, raise_errors=False)
        assert len(validated_df) == 2


class TestDataSourceRegistration:
    """Test data source registration."""
    
    def test_data_sources_registered(self):
        """Test that new data sources are registered."""
        from modules.data_sources import list_sources
        
        sources = list_sources()
        source_ids = [s.source_id for s in sources]
        
        assert 'worldbank_indicators' in source_ids
        assert 'imf_exchange_rates' in source_ids
        assert 'oecd_cli' in source_ids
        assert 'bls_data' in source_ids
        assert 'census_data' in source_ids
        assert 'eia_data' in source_ids
    
    def test_data_source_metadata(self):
        """Test data source metadata is correct."""
        from modules.data_sources import get_source
        
        # Test World Bank
        wb = get_source('worldbank_indicators')
        assert wb.source_name == 'World Bank Economic Indicators'
        assert wb.table_name == 'worldbank_indicators'
        assert wb.validation_type == 'worldbank'
        assert 'worldbank' in wb.tags
        
        # Test BLS
        bls = get_source('bls_data')
        assert bls.source_name == 'BLS Employment and CPI Data'
        assert bls.table_name == 'bls_data'
        assert bls.validation_type == 'bls'
        assert 'employment' in bls.tags


class TestDatabaseModels:
    """Test database models for new data sources."""
    
    def test_worldbank_model(self):
        """Test World Bank model exists and has correct structure."""
        from modules.database.models import WorldBankIndicators
        
        assert WorldBankIndicators.__tablename__ == 'worldbank_indicators'
        assert hasattr(WorldBankIndicators, 'country_code')
        assert hasattr(WorldBankIndicators, 'indicator_code')
        assert hasattr(WorldBankIndicators, 'year')
        assert hasattr(WorldBankIndicators, 'value')
    
    def test_imf_models(self):
        """Test IMF models exist."""
        from modules.database.models import IMFExchangeRates, IMFIndicators
        
        assert IMFExchangeRates.__tablename__ == 'imf_exchange_rates'
        assert IMFIndicators.__tablename__ == 'imf_indicators'
    
    def test_oecd_model(self):
        """Test OECD model exists."""
        from modules.database.models import OECDIndicators
        
        assert OECDIndicators.__tablename__ == 'oecd_indicators'
        assert hasattr(OECDIndicators, 'country_code')
        assert hasattr(OECDIndicators, 'indicator')
    
    def test_bls_model(self):
        """Test BLS model exists."""
        from modules.database.models import BLSData
        
        assert BLSData.__tablename__ == 'bls_data'
        assert hasattr(BLSData, 'series_id')
        assert hasattr(BLSData, 'period')
    
    def test_census_model(self):
        """Test Census model exists."""
        from modules.database.models import CensusData
        
        assert CensusData.__tablename__ == 'census_data'
        assert hasattr(CensusData, 'indicator')
    
    def test_eia_model(self):
        """Test EIA model exists."""
        from modules.database.models import EIAData
        
        assert EIAData.__tablename__ == 'eia_data'
        assert hasattr(EIAData, 'series_id')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
