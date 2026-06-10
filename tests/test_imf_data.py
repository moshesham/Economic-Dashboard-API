"""
Tests for IMF SDMX Data Loader Module
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from modules.imf_data import (
    to_iso3,
    find_column_by_names,
    IMFSDMXDataLoader,
    fetch_imf_exchange_rates,
    fetch_imf_indicator,
    fetch_imf_world_economic_outlook,
    refresh_imf_data
)


def test_to_iso3():
    """Test country code standardization."""
    assert to_iso3('US') == 'USA'
    assert to_iso3('us') == 'USA'
    assert to_iso3('USA') == 'USA'
    assert to_iso3('DE') == 'DEU'
    assert to_iso3('unknown_code') == 'UNKNOWN_CODE'


def test_find_column_by_names():
    """Test helper finding active columns."""
    columns = ['REF_AREA', 'OBS_VALUE', 'TIME_PERIOD']
    assert find_column_by_names(columns, ['COUNTRY', 'REF_AREA']) == 'REF_AREA'
    assert find_column_by_names(columns, ['value', 'OBS_VALUE']) == 'OBS_VALUE'
    assert find_column_by_names(columns, ['TIME_PERIOD', 'PERIOD']) == 'TIME_PERIOD'
    assert find_column_by_names(columns, ['NON_EXISTENT']) is None


@patch('modules.imf_data.sdmx.Client')
def test_imf_sdmx_data_loader_fetch_raw(mock_sdmx_client):
    """Test raw fetching using a mocked sdmx client."""
    mock_client_instance = MagicMock()
    mock_sdmx_client.return_value = mock_client_instance
    
    # Create sample SDMX returned Series/DataFrame
    sample_df = pd.DataFrame({
        'COUNTRY': ['USA', 'CHN'],
        'TIME_PERIOD': ['2023', '2023'],
        'OBS_VALUE': [1.0, 7.0]
    })
    
    with patch('modules.imf_data.sdmx.to_pandas', return_value=sample_df):
        loader = IMFSDMXDataLoader()
        df = loader.fetch_raw('ER', 'USA+CHN.XDC_USD.EOP_RT.A')
        
        assert not df.empty
        assert 'COUNTRY' in df.columns
        assert 'OBS_VALUE' in df.columns
        assert df.iloc[0]['COUNTRY'] == 'USA'


@patch('modules.imf_data.IMFSDMXDataLoader.fetch_raw')
def test_fetch_imf_exchange_rates(mock_fetch_raw):
    """Test fetching exchange rates maps to legacy schema."""
    sample_raw = pd.DataFrame({
        'COUNTRY': ['USA', 'CHN'],
        'TIME_PERIOD': ['2023', '2023'],
        'OBS_VALUE': [1.0, 7.0]
    })
    mock_fetch_raw.return_value = sample_raw
    
    df = fetch_imf_exchange_rates(countries=['US', 'CN'])
    
    assert not df.empty
    assert 'country_code' in df.columns
    assert 'exchange_rate' in df.columns
    assert 'indicator' in df.columns
    assert 'indicator_name' in df.columns
    assert 'date' in df.columns
    
    # USA maps back to US, CHN to CN
    assert df.loc[df['country_code'] == 'US', 'exchange_rate'].values[0] == 1.0
    assert df.loc[df['country_code'] == 'CN', 'exchange_rate'].values[0] == 7.0


@patch('modules.imf_data.IMFSDMXDataLoader.fetch_raw')
def test_fetch_imf_indicator(mock_fetch_raw):
    """Test fetching standard WEO indicator."""
    sample_raw = pd.DataFrame({
        'COUNTRY': ['DEU', 'JPN'],
        'TIME_PERIOD': ['2023', '2023'],
        'OBS_VALUE': [2.5, 1.2]
    })
    mock_fetch_raw.return_value = sample_raw
    
    df = fetch_imf_indicator('NGDP_RPCH', countries=['DE', 'JP'])
    
    assert not df.empty
    assert 'country_code' in df.columns
    assert 'value' in df.columns
    assert df.loc[df['country_code'] == 'DE', 'value'].values[0] == 2.5
    assert df.loc[df['country_code'] == 'JP', 'value'].values[0] == 1.2


@patch('modules.imf_data.fetch_imf_indicator')
def test_fetch_imf_world_economic_outlook(mock_fetch_indicator):
    """Test fetch_imf_world_economic_outlook consolidates multiple indicators."""
    mock_fetch_indicator.side_effect = lambda ind, *args, **kwargs: pd.DataFrame({
        'country_code': ['US'],
        'year': [2023],
        'value': [3.1],
        'indicator': [ind],
        'date': [pd.to_datetime('2023-12-31')]
    })
    
    df = fetch_imf_world_economic_outlook()
    
    assert not df.empty
    assert len(df) == 4  # 4 common WEO indicators
    assert set(df['indicator'].unique()) == {'NGDP_RPCH', 'PCPIPCH', 'LUR', 'GGX_NGDP'}


@patch('modules.database.queries.insert_generic_data')
@patch('modules.imf_data.fetch_imf_exchange_rates')
@patch('modules.imf_data.fetch_imf_world_economic_outlook')
def test_refresh_imf_data(mock_fetch_weo, mock_fetch_rates, mock_insert):
    """Test database refresh integration calls both loaders and inserts records."""
    mock_fetch_rates.return_value = pd.DataFrame([{'country_code': 'US', 'exchange_rate': 1.0}])
    mock_fetch_weo.return_value = pd.DataFrame([{'country_code': 'US', 'value': 2.0}])
    mock_insert.return_value = 5
    
    total = refresh_imf_data(include_exchange_rates=True, include_weo=True)
    
    assert total == 10  # 5 + 5
    assert mock_fetch_rates.called
    assert mock_fetch_weo.called
    assert mock_insert.call_count == 2
