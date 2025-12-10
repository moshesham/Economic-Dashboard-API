"""
Data Validation Module

Provides schema validation for data ingestion from various sources.
Uses Pandera for DataFrame validation.
"""

import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DataValidator:
    """Base class for data validators."""
    
    def __init__(self, schema: DataFrameSchema):
        self.schema = schema
    
    def validate(self, df: pd.DataFrame, raise_errors: bool = True) -> pd.DataFrame:
        """
        Validate a DataFrame against the schema.
        
        Args:
            df: DataFrame to validate
            raise_errors: If True, raise errors on validation failure
            
        Returns:
            Validated DataFrame (with coercions applied)
        """
        try:
            validated_df = self.schema.validate(df, lazy=True)
            logger.info(f"Validation passed: {len(validated_df)} records")
            return validated_df
        except pa.errors.SchemaErrors as e:
            logger.error(f"Validation failed: {e}")
            if raise_errors:
                raise
            # Return original DataFrame if not raising errors
            return df


# FRED Data Schema
fred_schema = DataFrameSchema({
    "series_id": Column(str, nullable=False),
    "date": Column(pd.Timestamp, nullable=False, coerce=True),
    "value": Column(float, nullable=True),
}, strict=False)  # Allow additional columns


# Stock OHLCV Schema
stock_ohlcv_schema = DataFrameSchema({
    "ticker": Column(str, nullable=False, checks=Check.str_length(min_value=1, max_value=20)),
    "date": Column(pd.Timestamp, nullable=False, coerce=True),
    "open": Column(float, nullable=True, checks=Check.greater_than_or_equal_to(0)),
    "high": Column(float, nullable=True, checks=Check.greater_than_or_equal_to(0)),
    "low": Column(float, nullable=True, checks=Check.greater_than_or_equal_to(0)),
    "close": Column(float, nullable=False, checks=Check.greater_than_or_equal_to(0)),
    "volume": Column(int, nullable=True, checks=Check.greater_than_or_equal_to(0)),
    "adj_close": Column(float, nullable=True, checks=Check.greater_than_or_equal_to(0)),
}, strict=False, coerce=True)


# Options Data Schema
options_schema = DataFrameSchema({
    "ticker": Column(str, nullable=False),
    "date": Column(pd.Timestamp, nullable=False, coerce=True),
    "expiration_date": Column(pd.Timestamp, nullable=False, coerce=True),
    "put_volume": Column(int, nullable=True, checks=Check.greater_than_or_equal_to(0)),
    "call_volume": Column(int, nullable=True, checks=Check.greater_than_or_equal_to(0)),
    "put_open_interest": Column(int, nullable=True, checks=Check.greater_than_or_equal_to(0)),
    "call_open_interest": Column(int, nullable=True, checks=Check.greater_than_or_equal_to(0)),
    "put_call_volume_ratio": Column(float, nullable=True),
    "put_call_oi_ratio": Column(float, nullable=True),
}, strict=False)


# ICI ETF Weekly Flows Schema
ici_weekly_flows_schema = DataFrameSchema({
    "week_ending": Column(pd.Timestamp, nullable=False, coerce=True),
    "fund_type": Column(str, nullable=False),
    "estimated_flows": Column(float, nullable=True),
    "total_net_assets": Column(float, nullable=True),
}, strict=False)


# CBOE VIX History Schema
cboe_vix_schema = DataFrameSchema({
    "date": Column(pd.Timestamp, nullable=False, coerce=True),
    "open": Column(float, nullable=True, checks=Check.greater_than_or_equal_to(0)),
    "high": Column(float, nullable=True, checks=Check.greater_than_or_equal_to(0)),
    "low": Column(float, nullable=True, checks=Check.greater_than_or_equal_to(0)),
    "close": Column(float, nullable=False, checks=Check.greater_than_or_equal_to(0)),
}, strict=False)


# Technical Features Schema
technical_features_schema = DataFrameSchema({
    "ticker": Column(str, nullable=False),
    "date": Column(pd.Timestamp, nullable=False, coerce=True),
    "rsi_14": Column(float, nullable=True, checks=Check.in_range(0, 100)),
    "rsi_28": Column(float, nullable=True, checks=Check.in_range(0, 100)),
    # Add more technical indicators as needed
}, strict=False)


# ML Predictions Schema
ml_predictions_schema = DataFrameSchema({
    "ticker": Column(str, nullable=False),
    "prediction_date": Column(pd.Timestamp, nullable=False, coerce=True),
    "target_date": Column(pd.Timestamp, nullable=False, coerce=True),
    "horizon_days": Column(int, nullable=False, checks=Check.greater_than(0)),
    "model_name": Column(str, nullable=False),
    "predicted_return": Column(float, nullable=True),
    "predicted_direction": Column(int, nullable=True, checks=Check.isin([-1, 0, 1])),
    "confidence": Column(float, nullable=True, checks=Check.in_range(0, 1)),
}, strict=False)


# SEC Filings Schema
sec_filings_schema = DataFrameSchema({
    "accession_number": Column(str, nullable=False),
    "cik": Column(str, nullable=False),
    "company_name": Column(str, nullable=True),
    "form_type": Column(str, nullable=False),
    "filing_date": Column(pd.Timestamp, nullable=True, coerce=True),
    "report_date": Column(pd.Timestamp, nullable=True, coerce=True),
}, strict=False)


# Validator instances
class FREDValidator(DataValidator):
    """Validator for FRED economic data."""
    def __init__(self):
        super().__init__(fred_schema)


class StockOHLCVValidator(DataValidator):
    """Validator for stock OHLCV data."""
    def __init__(self):
        super().__init__(stock_ohlcv_schema)


class OptionsValidator(DataValidator):
    """Validator for options data."""
    def __init__(self):
        super().__init__(options_schema)


class ICIWeeklyFlowsValidator(DataValidator):
    """Validator for ICI weekly ETF flows."""
    def __init__(self):
        super().__init__(ici_weekly_flows_schema)


class CBOEVIXValidator(DataValidator):
    """Validator for CBOE VIX historical data."""
    def __init__(self):
        super().__init__(cboe_vix_schema)


class TechnicalFeaturesValidator(DataValidator):
    """Validator for technical features."""
    def __init__(self):
        super().__init__(technical_features_schema)


class MLPredictionsValidator(DataValidator):
    """Validator for ML predictions."""
    def __init__(self):
        super().__init__(ml_predictions_schema)


class SECFilingsValidator(DataValidator):
    """Validator for SEC filings."""
    def __init__(self):
        super().__init__(sec_filings_schema)


# Factory function
def get_validator(data_type: str) -> DataValidator:
    """
    Get appropriate validator for a data type.
    
    Args:
        data_type: Type of data ('fred', 'stock', 'options', etc.)
        
    Returns:
        Appropriate validator instance
    """
    validators = {
        'fred': FREDValidator,
        'stock': StockOHLCVValidator,
        'stock_ohlcv': StockOHLCVValidator,
        'yfinance': StockOHLCVValidator,
        'options': OptionsValidator,
        'ici_weekly': ICIWeeklyFlowsValidator,
        'cboe_vix': CBOEVIXValidator,
        'technical_features': TechnicalFeaturesValidator,
        'ml_predictions': MLPredictionsValidator,
        'sec_filings': SECFilingsValidator,
    }
    
    data_type = data_type.lower()
    if data_type not in validators:
        raise ValueError(f"Unknown data type: {data_type}. Available: {list(validators.keys())}")
    
    return validators[data_type]()


# Utility functions
def validate_and_clean(df: pd.DataFrame, data_type: str, raise_errors: bool = False) -> pd.DataFrame:
    """
    Validate and clean a DataFrame.
    
    Args:
        df: DataFrame to validate
        data_type: Type of data
        raise_errors: If True, raise errors on validation failure
        
    Returns:
        Validated and cleaned DataFrame
    """
    validator = get_validator(data_type)
    validated_df = validator.validate(df, raise_errors=raise_errors)
    
    # Remove duplicates based on primary key columns
    pk_columns = _get_primary_key_columns(data_type)
    if pk_columns:
        before_count = len(validated_df)
        validated_df = validated_df.drop_duplicates(subset=pk_columns, keep='last')
        after_count = len(validated_df)
        
        if before_count > after_count:
            logger.warning(f"Removed {before_count - after_count} duplicate records")
    
    return validated_df


def _get_primary_key_columns(data_type: str) -> list:
    """Get primary key columns for a data type."""
    pk_mappings = {
        'fred': ['series_id', 'date'],
        'stock': ['ticker', 'date'],
        'stock_ohlcv': ['ticker', 'date'],
        'yfinance': ['ticker', 'date'],
        'options': ['ticker', 'date', 'expiration_date'],
        'ici_weekly': ['week_ending', 'fund_type'],
        'cboe_vix': ['date'],
        'technical_features': ['ticker', 'date'],
        'ml_predictions': ['ticker', 'prediction_date', 'target_date', 'model_name'],
        'sec_filings': ['accession_number'],
    }
    
    return pk_mappings.get(data_type.lower(), [])
