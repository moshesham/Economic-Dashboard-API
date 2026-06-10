"""
Tests for US Census Bureau Data Loader Module
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from modules.census_data import (
    CensusBureauDataLoader,
    fetch_census_retail_sales,
    fetch_census_housing_starts,
    fetch_census_trade,
    refresh_census_data
)


@patch('modules.census_data.CensusBureauDataLoader.fetch_eits_data')
def test_fetch_census_retail_sales(mock_fetch_eits):
    """Test fetching retail sales sets the correct indicator."""
    mock_fetch_eits.return_value = pd.DataFrame([
        {'date': '2023-01-01', 'category': '44000', 'value': 5000.0, 'seasonally_adjusted': True}
    ])
    
    df = fetch_census_retail_sales(api_key='test_key', start_year=2023)
    
    assert not df.empty
    assert df.iloc[0]['indicator'] == 'RETAIL_SALES'
    assert df.iloc[0]['value'] == 5000.0


@patch('modules.census_data.CensusBureauDataLoader.fetch_eits_data')
def test_fetch_census_housing_starts(mock_fetch_eits):
    """Test fetching housing starts sets the correct indicator."""
    mock_fetch_eits.return_value = pd.DataFrame([
        {'date': '2023-01-01', 'category': 'TOTAL', 'value': 1200.0, 'seasonally_adjusted': True}
    ])
    
    df = fetch_census_housing_starts(api_key='test_key', start_year=2023)
    
    assert not df.empty
    assert df.iloc[0]['indicator'] == 'HOUSING_STARTS'


@patch('modules.census_data.CensusBureauDataLoader.fetch_trade_data')
def test_fetch_census_trade(mock_fetch_trade):
    """Test fetching trade data calls loader helper."""
    mock_fetch_trade.return_value = pd.DataFrame([
        {'date': '2023-01-01', 'value': 25000.0, 'indicator': 'EXPORTS'}
    ])
    
    df = fetch_census_trade(api_key='test_key', start_year=2023, trade_type='exports')
    
    assert not df.empty
    assert df.iloc[0]['indicator'] == 'EXPORTS'
    mock_fetch_trade.assert_called_once_with('exports', 2023)


@patch('modules.database.queries.insert_generic_data')
@patch('modules.census_data.fetch_census_retail_sales')
@patch('modules.census_data.fetch_census_housing_starts')
@patch('modules.census_data.fetch_census_trade')
def test_refresh_census_data(mock_fetch_trade, mock_fetch_housing, mock_fetch_retail, mock_insert):
    """Test database refresh integration calls loaders and inserts."""
    mock_fetch_retail.return_value = pd.DataFrame([{'date': '2023-01-01', 'indicator': 'RETAIL_SALES'}])
    mock_fetch_housing.return_value = pd.DataFrame([{'date': '2023-01-01', 'indicator': 'HOUSING_STARTS'}])
    mock_fetch_trade.return_value = pd.DataFrame([{'date': '2023-01-01', 'indicator': 'EXPORTS'}])
    mock_insert.return_value = 10
    
    total = refresh_census_data(api_key='test_key')
    
    assert total == 40  # 10 * 4 calls (retail, housing, exports, imports)
    assert mock_fetch_retail.called
    assert mock_fetch_housing.called
    assert mock_fetch_trade.call_count == 2
    assert mock_insert.call_count == 4
