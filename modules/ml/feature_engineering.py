"""
Advanced Feature Engineering Module

Comprehensive feature generation for ML models including:
- Time-series features (lags, rolling windows, seasonality)
- Technical indicators (RSI, MACD, Bollinger Bands, ATR, etc.)
- Fundamental features (valuations, growth rates)
- Market microstructure (volume profiles, orderbook imbalances)
- Alternative data (sentiment, news momentum)
- Cross-asset features (correlations, regime indicators)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FeatureConfig:
    """Configuration for feature generation."""
    
    # Time-series lags
    price_lags: List[int] = None
    volume_lags: List[int] = None
    
    # Rolling windows
    ma_windows: List[int] = None
    volatility_windows: List[int] = None
    
    # Technical indicators
    rsi_periods: List[int] = None
    macd_config: Dict[str, int] = None
    bb_period: int = 20
    bb_std: float = 2.0
    atr_period: int = 14
    
    # Feature flags
    include_cyclical: bool = True
    include_interaction: bool = True
    include_regime: bool = True

    # Expensive time-series features (rolling apply)
    include_autocorr: bool = False
    include_hurst: bool = False
    
    def __post_init__(self):
        """Set defaults for None values."""
        if self.price_lags is None:
            self.price_lags = [1, 2, 3, 5, 10, 20]
        if self.volume_lags is None:
            self.volume_lags = [1, 2, 3, 5]
        if self.ma_windows is None:
            self.ma_windows = [5, 10, 20, 50, 200]
        if self.volatility_windows is None:
            self.volatility_windows = [5, 10, 20, 60]
        if self.rsi_periods is None:
            self.rsi_periods = [14, 28]
        if self.macd_config is None:
            self.macd_config = {'fast': 12, 'slow': 26, 'signal': 9}


class FeatureEngineer:
    """
    Advanced feature engineering for time-series financial data.
    
    Generates hundreds of features from OHLCV data and additional data sources.
    """
    
    def __init__(self, config: Optional[FeatureConfig] = None):
        """
        Initialize feature engineer.
        
        Args:
            config: Feature configuration, uses defaults if None
        """
        self.config = config or FeatureConfig()
        self.feature_names: List[str] = []
        
    def generate_all_features(
        self,
        ohlcv_data: pd.DataFrame,
        technical_data: Optional[pd.DataFrame] = None,
        fundamental_data: Optional[pd.DataFrame] = None,
        alternative_data: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Generate all features from available data sources.
        
        Args:
            ohlcv_data: DataFrame with OHLCV columns
            technical_data: Optional pre-computed technical indicators
            fundamental_data: Optional fundamental data
            alternative_data: Optional alternative data (sentiment, etc.)
            
        Returns:
            DataFrame with all generated features
        """
        features = pd.DataFrame(index=ohlcv_data.index)
        
        # Price-based features
        features = pd.concat([features, self._price_features(ohlcv_data)], axis=1)
        
        # Volume-based features
        features = pd.concat([features, self._volume_features(ohlcv_data)], axis=1)
        
        # Technical indicators
        features = pd.concat([features, self._technical_indicators(ohlcv_data)], axis=1)
        
        # Time-series patterns
        features = pd.concat([features, self._timeseries_features(ohlcv_data)], axis=1)
        
        # Cyclical features (day of week, month, etc.)
        if self.config.include_cyclical:
            features = pd.concat([features, self._cyclical_features(ohlcv_data)], axis=1)
        
        # Interaction features
        if self.config.include_interaction:
            features = pd.concat([features, self._interaction_features(features)], axis=1)
        
        # Market regime features
        if self.config.include_regime:
            features = pd.concat([features, self._regime_features(ohlcv_data)], axis=1)
        
        # Add pre-computed technical data if available
        if technical_data is not None:
            features = pd.concat([features, technical_data], axis=1)
        
        # Add fundamental features if available
        if fundamental_data is not None:
            features = pd.concat([features, self._fundamental_features(fundamental_data)], axis=1)
        
        # Add alternative data features if available
        if alternative_data is not None:
            features = pd.concat([features, alternative_data], axis=1)
        
        self.feature_names = features.columns.tolist()
        logger.info(f"Generated {len(self.feature_names)} features")
        
        return features
    
    def _price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate price-based features."""
        features = pd.DataFrame(index=df.index)
        
        # Returns at different horizons
        for lag in self.config.price_lags:
            features[f'return_{lag}d'] = df['close'].pct_change(lag)
            features[f'log_return_{lag}d'] = np.log(df['close'] / df['close'].shift(lag))
        
        # Intraday range
        features['intraday_range'] = (df['high'] - df['low']) / df['close']
        features['high_low_ratio'] = df['high'] / df['low']
        
        # Gap features
        gap = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
        features['gap'] = gap
        features['gap_filled'] = ((df['low'] <= df['close'].shift(1)) & (gap > 0)).astype(int)
        
        # Price position within range
        features['close_position'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-10)
        
        # Distance from moving averages
        for window in self.config.ma_windows:
            ma = df['close'].rolling(window).mean()
            features[f'dist_from_ma{window}'] = (df['close'] - ma) / ma
            features[f'above_ma{window}'] = (df['close'] > ma).astype(int)
        
        # Price momentum (Rate of Change)
        for period in [5, 10, 20]:
            features[f'roc_{period}d'] = ((df['close'] - df['close'].shift(period)) / 
                                          df['close'].shift(period) * 100)
        
        return features
    
    def _volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate volume-based features."""
        features = pd.DataFrame(index=df.index)
        
        # Volume changes
        for lag in self.config.volume_lags:
            features[f'volume_change_{lag}d'] = df['volume'].pct_change(lag)
        
        # Volume moving averages
        for window in [5, 10, 20]:
            features[f'volume_ma{window}'] = df['volume'].rolling(window).mean()
            features[f'volume_ratio_ma{window}'] = df['volume'] / features[f'volume_ma{window}']
        
        # On-Balance Volume (OBV)
        obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        features['obv'] = obv
        features['obv_slope_5d'] = obv.diff(5)
        
        # Volume-Price Trend (VPT)
        vpt = (df['volume'] * df['close'].pct_change()).fillna(0).cumsum()
        features['vpt'] = vpt
        
        # Money Flow Index components
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        money_flow = typical_price * df['volume']
        features['money_flow_ratio_5d'] = money_flow.rolling(5).mean() / money_flow.rolling(20).mean()
        
        return features
    
    def _technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate technical indicator features."""
        features = pd.DataFrame(index=df.index)
        
        # RSI for multiple periods
        for period in self.config.rsi_periods:
            features[f'rsi_{period}'] = self._calculate_rsi(df['close'], period)
        
        # MACD
        macd_data = self._calculate_macd(
            df['close'],
            self.config.macd_config['fast'],
            self.config.macd_config['slow'],
            self.config.macd_config['signal']
        )
        features['macd'] = macd_data['macd']
        features['macd_signal'] = macd_data['signal']
        features['macd_histogram'] = macd_data['histogram']
        
        # Bollinger Bands
        bb_data = self._calculate_bollinger_bands(
            df['close'],
            self.config.bb_period,
            self.config.bb_std
        )
        features['bb_upper'] = bb_data['upper']
        features['bb_middle'] = bb_data['middle']
        features['bb_lower'] = bb_data['lower']
        features['bb_width'] = (bb_data['upper'] - bb_data['lower']) / bb_data['middle']
        features['bb_position'] = (df['close'] - bb_data['lower']) / (bb_data['upper'] - bb_data['lower'] + 1e-10)
        
        # ATR (Average True Range)
        features['atr'] = self._calculate_atr(df, self.config.atr_period)
        features['atr_pct'] = features['atr'] / df['close'] * 100
        
        # Stochastic Oscillator
        stoch_data = self._calculate_stochastic(df, 14, 3)
        features['stoch_k'] = stoch_data['k']
        features['stoch_d'] = stoch_data['d']
        
        # Average Directional Index (ADX)
        features['adx'] = self._calculate_adx(df, 14)
        
        # Commodity Channel Index (CCI)
        features['cci'] = self._calculate_cci(df, 20)
        
        return features
    
    def _timeseries_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate time-series statistical features."""
        features = pd.DataFrame(index=df.index)
        
        returns = df['close'].pct_change()
        
        # Rolling volatility
        for window in self.config.volatility_windows:
            features[f'volatility_{window}d'] = returns.rolling(window).std() * np.sqrt(252)
            features[f'volatility_rank_{window}d'] = (
                features[f'volatility_{window}d'].rank(pct=True)
            )
        
        # Rolling skewness and kurtosis
        for window in [20, 60]:
            features[f'skew_{window}d'] = returns.rolling(window).skew()
            features[f'kurtosis_{window}d'] = returns.rolling(window).kurt()
        
        # Autocorrelation (expensive)
        if self.config.include_autocorr:
            for lag in [1, 5, 10]:
                features[f'autocorr_lag{lag}'] = returns.rolling(60).apply(
                    lambda x: x.autocorr(lag=lag) if len(x) > lag else np.nan
                )

        # Hurst exponent (trend strength, expensive)
        if self.config.include_hurst:
            features['hurst_60d'] = returns.rolling(60).apply(self._calculate_hurst)
        
        # Drawdown features
        cummax = df['close'].cummax()
        features['drawdown'] = (df['close'] - cummax) / cummax
        features['drawdown_duration'] = self._calculate_drawdown_duration(df['close'])
        
        return features
    
    def _cyclical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate cyclical time features."""
        features = pd.DataFrame(index=df.index)
        
        # Day of week (sin/cos encoding to capture cyclicality)
        day_of_week = df.index.dayofweek
        features['dow_sin'] = np.sin(2 * np.pi * day_of_week / 7)
        features['dow_cos'] = np.cos(2 * np.pi * day_of_week / 7)
        
        # Day of month
        day_of_month = df.index.day
        features['dom_sin'] = np.sin(2 * np.pi * day_of_month / 31)
        features['dom_cos'] = np.cos(2 * np.pi * day_of_month / 31)
        
        # Month of year
        month = df.index.month
        features['month_sin'] = np.sin(2 * np.pi * month / 12)
        features['month_cos'] = np.cos(2 * np.pi * month / 12)
        
        # Quarter
        quarter = df.index.quarter
        features['quarter_sin'] = np.sin(2 * np.pi * quarter / 4)
        features['quarter_cos'] = np.cos(2 * np.pi * quarter / 4)
        
        # Binary features for special days
        features['is_month_start'] = df.index.is_month_start.astype(int)
        features['is_month_end'] = df.index.is_month_end.astype(int)
        features['is_quarter_start'] = df.index.is_quarter_start.astype(int)
        features['is_quarter_end'] = df.index.is_quarter_end.astype(int)
        
        return features
    
    def _interaction_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """Generate interaction features between key indicators."""
        interactions = pd.DataFrame(index=features.index)
        
        # Volume-Price interactions
        if 'return_1d' in features.columns and 'volume_change_1d' in features.columns:
            interactions['volume_price_interaction'] = (
                features['return_1d'] * features['volume_change_1d']
            )
        
        # Volatility-Momentum interactions
        if 'volatility_20d' in features.columns and 'roc_20d' in features.columns:
            interactions['vol_momentum_ratio'] = (
                features['roc_20d'] / (features['volatility_20d'] + 1e-10)
            )
        
        # RSI-Price distance interactions
        if 'rsi_14' in features.columns and 'dist_from_ma50' in features.columns:
            interactions['rsi_ma_interaction'] = (
                features['rsi_14'] * features['dist_from_ma50']
            )
        
        return interactions
    
    def _regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate market regime indicator features."""
        features = pd.DataFrame(index=df.index)
        
        returns = df['close'].pct_change()
        
        # Trend regime (based on MA slopes and positions)
        ma_50 = df['close'].rolling(50).mean()
        ma_200 = df['close'].rolling(200).mean()
        
        features['bullish_regime'] = ((df['close'] > ma_50) & (ma_50 > ma_200)).astype(int)
        features['bearish_regime'] = ((df['close'] < ma_50) & (ma_50 < ma_200)).astype(int)
        features['ma_golden_cross'] = (ma_50 > ma_200).astype(int)
        
        # Volatility regime
        vol_20 = returns.rolling(20).std()
        vol_percentile = vol_20.rolling(252).rank(pct=True)
        features['high_vol_regime'] = (vol_percentile > 0.8).astype(int)
        features['low_vol_regime'] = (vol_percentile < 0.2).astype(int)
        
        # Trend strength
        adx_threshold = 25
        if 'adx' not in features.columns:
            features['adx_temp'] = self._calculate_adx(df, 14)
            features['trending_regime'] = (features['adx_temp'] > adx_threshold).astype(int)
            features = features.drop('adx_temp', axis=1)
        
        return features
    
    def _fundamental_features(self, fundamental_data: pd.DataFrame) -> pd.DataFrame:
        """Process and generate features from fundamental data."""
        features = pd.DataFrame(index=fundamental_data.index)
        
        # Calculate growth rates
        for col in fundamental_data.columns:
            if col not in ['date', 'ticker']:
                # YoY growth
                features[f'{col}_yoy_growth'] = fundamental_data[col].pct_change(4)  # Quarterly
                
                # QoQ growth
                features[f'{col}_qoq_growth'] = fundamental_data[col].pct_change()
                
                # Trend (linear regression slope over last 8 quarters)
                features[f'{col}_trend_8q'] = fundamental_data[col].rolling(8).apply(
                    lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) == 8 else np.nan
                )
        
        return features
    
    # Helper methods for technical indicators
    
    @staticmethod
    def _calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def _calculate_macd(
        prices: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Dict[str, pd.Series]:
        """Calculate MACD indicator."""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal).mean()
        histogram = macd - signal_line
        
        return {
            'macd': macd,
            'signal': signal_line,
            'histogram': histogram
        }
    
    @staticmethod
    def _calculate_bollinger_bands(
        prices: pd.Series,
        period: int = 20,
        num_std: float = 2.0
    ) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands."""
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper = middle + (std * num_std)
        lower = middle - (std * num_std)
        
        return {
            'upper': upper,
            'middle': middle,
            'lower': lower
        }
    
    @staticmethod
    def _calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        
        atr = true_range.rolling(period).mean()
        
        return atr
    
    @staticmethod
    def _calculate_stochastic(
        df: pd.DataFrame,
        k_period: int = 14,
        d_period: int = 3
    ) -> Dict[str, pd.Series]:
        """Calculate Stochastic Oscillator."""
        low_min = df['low'].rolling(window=k_period).min()
        high_max = df['high'].rolling(window=k_period).max()
        
        k = 100 * (df['close'] - low_min) / (high_max - low_min + 1e-10)
        d = k.rolling(window=d_period).mean()
        
        return {'k': k, 'd': d}
    
    @staticmethod
    def _calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index."""
        # Plus and Minus Directional Movement
        up_move = df['high'].diff()
        down_move = -df['low'].diff()
        
        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0)
        
        # True Range
        tr = FeatureEngineer._calculate_atr(df, 1)
        
        # Smoothed Plus/Minus DI
        plus_di = 100 * (plus_dm.rolling(period).mean() / tr.rolling(period).mean())
        minus_di = 100 * (minus_dm.rolling(period).mean() / tr.rolling(period).mean())
        
        # Directional Index
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        
        # ADX is smoothed DX
        adx = dx.rolling(period).mean()
        
        return adx
    
    @staticmethod
    def _calculate_cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate Commodity Channel Index."""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        sma = typical_price.rolling(period).mean()
        mad = typical_price.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean())
        
        cci = (typical_price - sma) / (0.015 * mad + 1e-10)
        
        return cci
    
    @staticmethod
    def _calculate_hurst(prices: np.ndarray) -> float:
        """Calculate Hurst exponent for trend detection."""
        if len(prices) < 20:
            return np.nan
        
        try:
            lags = range(2, min(20, len(prices) // 2))
            tau = [np.std(np.subtract(prices[lag:], prices[:-lag])) for lag in lags]
            
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            return poly[0]
        except:
            return np.nan
    
    @staticmethod
    def _calculate_drawdown_duration(prices: pd.Series) -> pd.Series:
        """Calculate number of periods in drawdown."""
        cummax = prices.cummax()
        is_drawdown = prices < cummax
        
        # Count consecutive drawdown periods
        drawdown_groups = (is_drawdown != is_drawdown.shift()).cumsum()
        duration = is_drawdown.groupby(drawdown_groups).cumsum()
        
        return duration
    
    def get_feature_importance_groups(self) -> Dict[str, List[str]]:
        """
        Group features by category for importance analysis.
        
        Returns:
            Dictionary mapping category names to lists of feature names
        """
        groups = {
            'price': [],
            'volume': [],
            'technical': [],
            'timeseries': [],
            'cyclical': [],
            'interaction': [],
            'regime': [],
            'fundamental': []
        }
        
        for feature in self.feature_names:
            if any(x in feature for x in ['return', 'gap', 'range', 'ma', 'roc']):
                groups['price'].append(feature)
            elif 'volume' in feature or 'obv' in feature or 'vpt' in feature:
                groups['volume'].append(feature)
            elif any(x in feature for x in ['rsi', 'macd', 'bb_', 'atr', 'stoch', 'adx', 'cci']):
                groups['technical'].append(feature)
            elif any(x in feature for x in ['volatility', 'skew', 'kurtosis', 'autocorr', 'hurst', 'drawdown']):
                groups['timeseries'].append(feature)
            elif any(x in feature for x in ['dow_', 'dom_', 'month_', 'quarter_', 'is_']):
                groups['cyclical'].append(feature)
            elif 'interaction' in feature or 'ratio' in feature:
                groups['interaction'].append(feature)
            elif 'regime' in feature or 'cross' in feature:
                groups['regime'].append(feature)
            elif any(x in feature for x in ['growth', 'trend', 'yoy', 'qoq']):
                groups['fundamental'].append(feature)
        
        return groups
