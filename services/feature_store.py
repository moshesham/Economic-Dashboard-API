"""
Feature Store - Centralized feature computation and caching.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class FeatureStore:
    """
    Centralized feature computation and storage.
    
    Features are computed once and cached in DuckDB for fast retrieval.
    The API reads pre-computed features rather than computing on-demand.
    
    Feature Categories:
    - Technical: Moving averages, momentum, volatility
    - Options-derived: IV metrics, put/call ratios, Greeks
    - Fundamental: Valuation ratios, financial health scores
    - Alternative: Sentiment, insider trading signals
    """
    
    def __init__(self, db_path: Optional[str] = None):
        from modules.database import get_db_connection
        self.db = get_db_connection(db_path)
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Create feature storage tables if they don't exist."""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS feature_store (
                ticker VARCHAR NOT NULL,
                feature_name VARCHAR NOT NULL,
                feature_value DOUBLE,
                computed_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP,
                metadata JSON,
                PRIMARY KEY (ticker, feature_name)
            )
        """)
        
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS feature_snapshots (
                ticker VARCHAR NOT NULL,
                snapshot_date DATE NOT NULL,
                features JSON NOT NULL,
                created_at TIMESTAMP NOT NULL,
                PRIMARY KEY (ticker, snapshot_date)
            )
        """)
        
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_feature_store_ticker 
            ON feature_store(ticker)
        """)
        
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_feature_store_expires 
            ON feature_store(expires_at)
        """)
    
    # =========================================================================
    # Feature Computation
    # =========================================================================
    
    def compute_and_store(self, ticker: str) -> Dict[str, Any]:
        """
        Compute all features for a ticker and store in database.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dictionary of computed features
        """
        ticker = ticker.upper()
        features = {}
        
        # Technical features
        try:
            technical = self._compute_technical_features(ticker)
            features.update(technical)
        except Exception as e:
            logger.error(f"Failed to compute technical features for {ticker}: {e}")
        
        # Options features
        try:
            options = self._compute_options_features(ticker)
            features.update(options)
        except Exception as e:
            logger.error(f"Failed to compute options features for {ticker}: {e}")
        
        # Fundamental features
        try:
            fundamental = self._compute_fundamental_features(ticker)
            features.update(fundamental)
        except Exception as e:
            logger.error(f"Failed to compute fundamental features for {ticker}: {e}")
        
        # Risk features
        try:
            risk = self._compute_risk_features(ticker)
            features.update(risk)
        except Exception as e:
            logger.error(f"Failed to compute risk features for {ticker}: {e}")
        
        # Store features
        self._store_features(ticker, features)
        
        # Store daily snapshot
        self._store_snapshot(ticker, features)
        
        logger.info(f"Computed {len(features)} features for {ticker}")
        return features
    
    def _compute_technical_features(self, ticker: str) -> Dict[str, float]:
        """Compute technical indicator features."""
        features = {}
        
        # Fetch price data
        result = self.db.query(f"""
            SELECT date, open, high, low, close, volume
            FROM stock_prices
            WHERE ticker = '{ticker}'
            ORDER BY date DESC
            LIMIT 200
        """)
        
        if result.empty:
            return features
        
        df = result.sort_values('date').reset_index(drop=True)
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        # Moving Averages
        for window in [5, 10, 20, 50, 200]:
            ma = close.rolling(window).mean().iloc[-1]
            features[f'ma_{window}'] = ma
            features[f'price_to_ma_{window}'] = close.iloc[-1] / ma if ma else None
        
        # Exponential Moving Averages
        for span in [12, 26]:
            ema = close.ewm(span=span).mean().iloc[-1]
            features[f'ema_{span}'] = ema
        
        # MACD
        ema_12 = close.ewm(span=12).mean()
        ema_26 = close.ewm(span=26).mean()
        macd = ema_12 - ema_26
        signal = macd.ewm(span=9).mean()
        features['macd'] = macd.iloc[-1]
        features['macd_signal'] = signal.iloc[-1]
        features['macd_histogram'] = macd.iloc[-1] - signal.iloc[-1]
        
        # RSI
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        features['rsi_14'] = rsi.iloc[-1]
        
        # Bollinger Bands
        bb_ma = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        features['bb_upper'] = (bb_ma + 2 * bb_std).iloc[-1]
        features['bb_lower'] = (bb_ma - 2 * bb_std).iloc[-1]
        features['bb_width'] = (features['bb_upper'] - features['bb_lower']) / bb_ma.iloc[-1]
        features['bb_position'] = (close.iloc[-1] - features['bb_lower']) / (features['bb_upper'] - features['bb_lower'])
        
        # Volatility
        returns = close.pct_change()
        features['volatility_5d'] = returns.tail(5).std() * np.sqrt(252)
        features['volatility_20d'] = returns.tail(20).std() * np.sqrt(252)
        features['volatility_60d'] = returns.tail(60).std() * np.sqrt(252)
        
        # Average True Range
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)
        features['atr_14'] = tr.rolling(14).mean().iloc[-1]
        features['atr_percent'] = features['atr_14'] / close.iloc[-1]
        
        # Volume metrics
        avg_volume = volume.rolling(20).mean().iloc[-1]
        features['avg_volume_20d'] = avg_volume
        features['volume_ratio'] = volume.iloc[-1] / avg_volume if avg_volume else None
        
        # Price momentum
        features['return_1d'] = returns.iloc[-1]
        features['return_5d'] = close.iloc[-1] / close.iloc[-5] - 1
        features['return_20d'] = close.iloc[-1] / close.iloc[-20] - 1
        features['return_60d'] = close.iloc[-1] / close.iloc[-60] - 1 if len(close) > 60 else None
        
        return features
    
    def _compute_options_features(self, ticker: str) -> Dict[str, float]:
        """Compute options-derived features."""
        features = {}
        
        result = self.db.query(f"""
            SELECT *
            FROM options_data
            WHERE ticker = '{ticker}'
            AND expiration > CURRENT_DATE
            ORDER BY expiration, strike
        """)
        
        if result.empty:
            return features
        
        # Separate calls and puts
        calls = result[result['option_type'] == 'call']
        puts = result[result['option_type'] == 'put']
        
        # Put/Call Ratios
        if not calls.empty and not puts.empty:
            features['put_call_ratio_volume'] = puts['volume'].sum() / max(calls['volume'].sum(), 1)
            features['put_call_ratio_oi'] = puts['open_interest'].sum() / max(calls['open_interest'].sum(), 1)
        
        # Implied Volatility
        atm_options = result[
            (result['strike'] >= result['underlying_price'] * 0.95) &
            (result['strike'] <= result['underlying_price'] * 1.05)
        ]
        if not atm_options.empty:
            features['iv_atm_mean'] = atm_options['implied_volatility'].mean()
            features['iv_atm_calls'] = calls[
                (calls['strike'] >= calls['underlying_price'] * 0.95) &
                (calls['strike'] <= calls['underlying_price'] * 1.05)
            ]['implied_volatility'].mean()
            features['iv_atm_puts'] = puts[
                (puts['strike'] >= puts['underlying_price'] * 0.95) &
                (puts['strike'] <= puts['underlying_price'] * 1.05)
            ]['implied_volatility'].mean()
        
        # IV Skew (OTM puts vs OTM calls)
        otm_puts = puts[puts['strike'] < puts['underlying_price'] * 0.95]
        otm_calls = calls[calls['strike'] > calls['underlying_price'] * 1.05]
        if not otm_puts.empty and not otm_calls.empty:
            features['iv_skew'] = otm_puts['implied_volatility'].mean() - otm_calls['implied_volatility'].mean()
        
        # Total options metrics
        features['total_call_volume'] = calls['volume'].sum()
        features['total_put_volume'] = puts['volume'].sum()
        features['total_call_oi'] = calls['open_interest'].sum()
        features['total_put_oi'] = puts['open_interest'].sum()
        
        return features
    
    def _compute_fundamental_features(self, ticker: str) -> Dict[str, float]:
        """Compute fundamental analysis features."""
        features = {}
        
        try:
            from modules.features.financial_health_scorer import FinancialHealthScorer
            scorer = FinancialHealthScorer()
            health = scorer.calculate_composite_health_score(ticker)
            
            if health:
                features['financial_health_score'] = health.get('composite_score')
                features['profitability_score'] = health.get('profitability_score')
                features['leverage_score'] = health.get('leverage_score')
                features['liquidity_score'] = health.get('liquidity_score')
                features['efficiency_score'] = health.get('efficiency_score')
        except Exception as e:
            logger.warning(f"Could not compute fundamental features for {ticker}: {e}")
        
        return features
    
    def _compute_risk_features(self, ticker: str) -> Dict[str, float]:
        """Compute risk-related features."""
        features = {}
        
        try:
            from modules.features.margin_risk_composite import MarginCallRiskCalculator
            calc = MarginCallRiskCalculator()
            risk = calc.calculate_composite_risk(ticker)
            
            if risk:
                features['margin_risk_score'] = risk.get('composite_score')
                features['margin_risk_leverage'] = risk.get('components', {}).get('leverage')
                features['margin_risk_volatility'] = risk.get('components', {}).get('volatility')
                features['margin_risk_options'] = risk.get('components', {}).get('options')
                features['margin_risk_liquidity'] = risk.get('components', {}).get('liquidity')
        except Exception as e:
            logger.warning(f"Could not compute risk features for {ticker}: {e}")
        
        return features
    
    # =========================================================================
    # Storage Operations
    # =========================================================================
    
    def _store_features(self, ticker: str, features: Dict[str, float], ttl_hours: int = 24):
        """Store features in database with TTL."""
        now = datetime.utcnow()
        expires = now + timedelta(hours=ttl_hours)
        
        for name, value in features.items():
            if value is not None and not np.isnan(value):
                self.db.execute(f"""
                    INSERT OR REPLACE INTO feature_store 
                    (ticker, feature_name, feature_value, computed_at, expires_at)
                    VALUES ('{ticker}', '{name}', {value}, '{now}', '{expires}')
                """)
    
    def _store_snapshot(self, ticker: str, features: Dict[str, float]):
        """Store daily feature snapshot."""
        import json
        now = datetime.utcnow()
        today = now.date()
        
        # Clean features for JSON
        clean_features = {
            k: float(v) if v is not None and not np.isnan(v) else None
            for k, v in features.items()
        }
        
        self.db.execute(f"""
            INSERT OR REPLACE INTO feature_snapshots
            (ticker, snapshot_date, features, created_at)
            VALUES ('{ticker}', '{today}', '{json.dumps(clean_features)}', '{now}')
        """)
    
    # =========================================================================
    # Retrieval Operations
    # =========================================================================
    
    def get_features(self, ticker: str, feature_names: Optional[List[str]] = None) -> Dict[str, float]:
        """
        Get cached features for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            feature_names: Optional list of specific features to retrieve
        
        Returns:
            Dictionary of feature values
        """
        ticker = ticker.upper()
        
        if feature_names:
            names_str = ", ".join(f"'{n}'" for n in feature_names)
            query = f"""
                SELECT feature_name, feature_value
                FROM feature_store
                WHERE ticker = '{ticker}'
                AND feature_name IN ({names_str})
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """
        else:
            query = f"""
                SELECT feature_name, feature_value
                FROM feature_store
                WHERE ticker = '{ticker}'
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """
        
        result = self.db.query(query)
        
        if result.empty:
            return {}
        
        return dict(zip(result['feature_name'], result['feature_value']))
    
    def get_snapshot(self, ticker: str, date: Optional[str] = None) -> Optional[Dict[str, float]]:
        """
        Get feature snapshot for a specific date.
        
        Args:
            ticker: Stock ticker symbol
            date: Date string (YYYY-MM-DD), defaults to today
        
        Returns:
            Feature dictionary or None
        """
        import json
        
        ticker = ticker.upper()
        date = date or datetime.utcnow().date().isoformat()
        
        result = self.db.query(f"""
            SELECT features
            FROM feature_snapshots
            WHERE ticker = '{ticker}'
            AND snapshot_date = '{date}'
        """)
        
        if result.empty:
            return None
        
        return json.loads(result['features'].iloc[0])
    
    def get_feature_history(
        self,
        ticker: str,
        feature_names: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get historical feature values from snapshots.
        
        Args:
            ticker: Stock ticker symbol
            feature_names: List of feature names
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            DataFrame with date index and feature columns
        """
        import json
        
        ticker = ticker.upper()
        start_date = start_date or (datetime.utcnow() - timedelta(days=30)).date().isoformat()
        end_date = end_date or datetime.utcnow().date().isoformat()
        
        result = self.db.query(f"""
            SELECT snapshot_date, features
            FROM feature_snapshots
            WHERE ticker = '{ticker}'
            AND snapshot_date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY snapshot_date
        """)
        
        if result.empty:
            return pd.DataFrame()
        
        records = []
        for _, row in result.iterrows():
            features = json.loads(row['features'])
            record = {'date': row['snapshot_date']}
            for name in feature_names:
                record[name] = features.get(name)
            records.append(record)
        
        return pd.DataFrame(records).set_index('date')
    
    # =========================================================================
    # Maintenance
    # =========================================================================
    
    def cleanup_expired(self) -> int:
        """Remove expired features. Returns count of deleted rows."""
        result = self.db.execute("""
            DELETE FROM feature_store
            WHERE expires_at IS NOT NULL
            AND expires_at < CURRENT_TIMESTAMP
        """)
        return result.rowcount if hasattr(result, 'rowcount') else 0
    
    def get_stale_tickers(self, max_age_hours: int = 4) -> List[str]:
        """Get tickers that need feature refresh."""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        result = self.db.query(f"""
            SELECT DISTINCT ticker
            FROM feature_store
            WHERE computed_at < '{cutoff}'
            OR ticker NOT IN (SELECT DISTINCT ticker FROM feature_store)
        """)
        
        return result['ticker'].tolist() if not result.empty else []


# Singleton instance
_feature_store: Optional[FeatureStore] = None


def get_feature_store() -> FeatureStore:
    """Get the feature store singleton."""
    global _feature_store
    if _feature_store is None:
        _feature_store = FeatureStore()
    return _feature_store
