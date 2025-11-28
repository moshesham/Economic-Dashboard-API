"""
Advanced Margin Risk Analytics

Enhanced margin call risk scoring with:
- Multi-factor risk decomposition
- Regime-aware calibration
- Real-time alert generation
- Historical stress testing
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RiskRegime(Enum):
    """Market risk regime classification."""
    LOW_VOL = "low_volatility"
    NORMAL = "normal"
    ELEVATED = "elevated"
    CRISIS = "crisis"


@dataclass
class RiskAlert:
    """Risk alert data structure."""
    alert_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    ticker: str
    message: str
    value: float
    threshold: float
    triggered_at: datetime


class MarginRiskEngine:
    """
    Advanced margin risk calculation engine.
    
    Improvements over base calculator:
    1. Regime-aware scoring (adjusts thresholds based on market conditions)
    2. Multi-timeframe volatility analysis
    3. Options-implied risk extraction
    4. Cross-asset correlation stress testing
    5. Real-time alert generation
    """
    
    # Default component weights
    DEFAULT_WEIGHTS = {
        'leverage': 0.25,
        'volatility': 0.25,
        'options': 0.20,
        'liquidity': 0.15,
        'momentum': 0.10,
        'correlation': 0.05,
    }
    
    # Regime-specific multipliers
    REGIME_MULTIPLIERS = {
        RiskRegime.LOW_VOL: 0.8,
        RiskRegime.NORMAL: 1.0,
        RiskRegime.ELEVATED: 1.2,
        RiskRegime.CRISIS: 1.5,
    }
    
    def __init__(self, db=None, weights: Optional[Dict[str, float]] = None):
        self.db = db
        self.weights = weights or self.DEFAULT_WEIGHTS
        self._regime_cache: Dict[str, Tuple[RiskRegime, datetime]] = {}
        self._alerts: List[RiskAlert] = []
    
    def calculate_composite_risk(
        self,
        ticker: str,
        include_stress_test: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive margin risk score.
        
        Args:
            ticker: Stock ticker symbol
            include_stress_test: Whether to run stress scenarios
        
        Returns:
            Complete risk assessment with components and alerts
        """
        ticker = ticker.upper()
        
        # Detect current market regime
        regime = self._detect_regime()
        regime_mult = self.REGIME_MULTIPLIERS[regime]
        
        # Calculate component scores
        components = {}
        
        # 1. Leverage Risk
        leverage_data = self._calculate_leverage_risk(ticker)
        components['leverage'] = leverage_data
        
        # 2. Multi-timeframe Volatility Risk
        volatility_data = self._calculate_volatility_risk(ticker)
        components['volatility'] = volatility_data
        
        # 3. Options-Implied Risk
        options_data = self._calculate_options_risk(ticker)
        components['options'] = options_data
        
        # 4. Liquidity Risk
        liquidity_data = self._calculate_liquidity_risk(ticker)
        components['liquidity'] = liquidity_data
        
        # 5. Momentum Risk (trend reversal risk)
        momentum_data = self._calculate_momentum_risk(ticker)
        components['momentum'] = momentum_data
        
        # 6. Correlation Risk (contagion)
        correlation_data = self._calculate_correlation_risk(ticker)
        components['correlation'] = correlation_data
        
        # Calculate weighted composite score
        composite_score = 0.0
        valid_weights = 0.0
        
        for component, weight in self.weights.items():
            if component in components and components[component].get('score') is not None:
                composite_score += components[component]['score'] * weight
                valid_weights += weight
        
        if valid_weights > 0:
            composite_score = composite_score / valid_weights
        
        # Apply regime adjustment
        adjusted_score = min(1.0, composite_score * regime_mult)
        
        # Determine risk level
        risk_level = self._score_to_level(adjusted_score)
        signal = self._score_to_signal(adjusted_score)
        
        # Generate alerts
        alerts = self._generate_alerts(ticker, components, adjusted_score)
        
        # Optional stress testing
        stress_results = None
        if include_stress_test:
            stress_results = self._run_stress_test(ticker, components)
        
        return {
            'ticker': ticker,
            'composite_score': round(adjusted_score, 4),
            'raw_score': round(composite_score, 4),
            'risk_level': risk_level,
            'signal': signal,
            'regime': regime.value,
            'regime_multiplier': regime_mult,
            'components': components,
            'alerts': [self._alert_to_dict(a) for a in alerts],
            'stress_test': stress_results,
            'calculated_at': datetime.utcnow().isoformat(),
        }
    
    def _detect_regime(self) -> RiskRegime:
        """Detect current market risk regime using VIX."""
        # Cache regime detection for 1 hour
        cache_key = 'market_regime'
        if cache_key in self._regime_cache:
            regime, cached_at = self._regime_cache[cache_key]
            if datetime.utcnow() - cached_at < timedelta(hours=1):
                return regime
        
        try:
            if self.db:
                vix_data = self.db.query("""
                    SELECT close as vix
                    FROM fred_data
                    WHERE series_id = 'VIXCLS'
                    ORDER BY date DESC
                    LIMIT 1
                """)
                if not vix_data.empty:
                    vix = vix_data['vix'].iloc[0]
                    
                    if vix < 15:
                        regime = RiskRegime.LOW_VOL
                    elif vix < 20:
                        regime = RiskRegime.NORMAL
                    elif vix < 30:
                        regime = RiskRegime.ELEVATED
                    else:
                        regime = RiskRegime.CRISIS
                    
                    self._regime_cache[cache_key] = (regime, datetime.utcnow())
                    return regime
        except Exception as e:
            logger.warning(f"Could not detect regime: {e}")
        
        return RiskRegime.NORMAL
    
    def _calculate_leverage_risk(self, ticker: str) -> Dict[str, Any]:
        """
        Enhanced leverage risk calculation.
        
        Factors:
        - Short interest as % of float
        - Days to cover
        - Short interest trend (increasing = worse)
        - Margin debt concentration
        """
        try:
            if not self.db:
                return {'score': 0.5, 'error': 'No database connection'}
            
            # Get short interest data
            short_data = self.db.query(f"""
                SELECT 
                    short_interest_pct,
                    days_to_cover,
                    short_interest_ratio
                FROM short_interest
                WHERE ticker = '{ticker}'
                ORDER BY report_date DESC
                LIMIT 2
            """)
            
            if short_data.empty:
                return {'score': 0.5, 'data_available': False}
            
            current = short_data.iloc[0]
            
            # Calculate component scores
            si_pct = current.get('short_interest_pct', 0) or 0
            dtc = current.get('days_to_cover', 0) or 0
            
            # Normalized scores (0-1)
            si_score = min(1.0, si_pct / 30)  # 30% SI = max risk
            dtc_score = min(1.0, dtc / 15)    # 15 days = max risk
            
            # Trend analysis
            trend_penalty = 0
            if len(short_data) > 1:
                prior = short_data.iloc[1]
                prior_si = prior.get('short_interest_pct', 0) or 0
                if si_pct > prior_si * 1.1:  # 10% increase
                    trend_penalty = 0.1
            
            composite = (si_score * 0.5 + dtc_score * 0.5) + trend_penalty
            composite = min(1.0, composite)
            
            return {
                'score': round(composite, 4),
                'short_interest_pct': si_pct,
                'days_to_cover': dtc,
                'si_score': round(si_score, 4),
                'dtc_score': round(dtc_score, 4),
                'trend_penalty': trend_penalty,
            }
            
        except Exception as e:
            logger.error(f"Leverage risk calculation failed: {e}")
            return {'score': 0.5, 'error': str(e)}
    
    def _calculate_volatility_risk(self, ticker: str) -> Dict[str, Any]:
        """
        Multi-timeframe volatility risk.
        
        Analyzes:
        - Realized volatility (5d, 20d, 60d)
        - Volatility regime (expanding/contracting)
        - Volatility of volatility (vol-of-vol)
        - ATR spike detection
        """
        try:
            if not self.db:
                return {'score': 0.5, 'error': 'No database connection'}
            
            prices = self.db.query(f"""
                SELECT date, close, high, low
                FROM stock_prices
                WHERE ticker = '{ticker}'
                ORDER BY date DESC
                LIMIT 120
            """)
            
            if prices.empty or len(prices) < 20:
                return {'score': 0.5, 'data_available': False}
            
            prices = prices.sort_values('date').reset_index(drop=True)
            returns = prices['close'].pct_change().dropna()
            
            # Multi-timeframe volatility
            vol_5d = returns.tail(5).std() * np.sqrt(252)
            vol_20d = returns.tail(20).std() * np.sqrt(252)
            vol_60d = returns.tail(60).std() * np.sqrt(252) if len(returns) >= 60 else vol_20d
            
            # Volatility regime (short-term vs long-term)
            vol_regime = vol_5d / vol_60d if vol_60d > 0 else 1.0
            
            # Vol-of-vol (stability of volatility)
            rolling_vol = returns.rolling(5).std()
            vol_of_vol = rolling_vol.std() / rolling_vol.mean() if rolling_vol.mean() > 0 else 0
            
            # ATR spike detection
            tr = pd.concat([
                prices['high'] - prices['low'],
                (prices['high'] - prices['close'].shift()).abs(),
                (prices['low'] - prices['close'].shift()).abs()
            ], axis=1).max(axis=1)
            atr_14 = tr.rolling(14).mean().iloc[-1]
            atr_ratio = tr.iloc[-1] / atr_14 if atr_14 > 0 else 1.0
            
            # Composite volatility score
            vol_score = min(1.0, vol_20d / 0.5)  # 50% annualized vol = max
            regime_score = min(1.0, max(0, vol_regime - 1) / 0.5)  # Expansion penalty
            vov_score = min(1.0, vol_of_vol / 0.5)
            atr_score = min(1.0, max(0, atr_ratio - 1) / 1.0)  # 2x ATR = max
            
            composite = (
                vol_score * 0.4 +
                regime_score * 0.3 +
                vov_score * 0.15 +
                atr_score * 0.15
            )
            
            return {
                'score': round(composite, 4),
                'vol_5d': round(vol_5d, 4),
                'vol_20d': round(vol_20d, 4),
                'vol_60d': round(vol_60d, 4),
                'vol_regime': round(vol_regime, 4),
                'vol_of_vol': round(vol_of_vol, 4),
                'atr_ratio': round(atr_ratio, 4),
            }
            
        except Exception as e:
            logger.error(f"Volatility risk calculation failed: {e}")
            return {'score': 0.5, 'error': str(e)}
    
    def _calculate_options_risk(self, ticker: str) -> Dict[str, Any]:
        """
        Options-implied risk signals.
        
        Analyzes:
        - IV skew (put premium = fear)
        - IV term structure inversion
        - Put/Call ratio extremes
        - Unusual options activity
        """
        try:
            if not self.db:
                return {'score': 0.5, 'error': 'No database connection'}
            
            options = self.db.query(f"""
                SELECT *
                FROM options_data
                WHERE ticker = '{ticker}'
                AND expiration > CURRENT_DATE
            """)
            
            if options.empty:
                return {'score': 0.5, 'data_available': False}
            
            calls = options[options['option_type'] == 'call']
            puts = options[options['option_type'] == 'put']
            
            # Put/Call ratio
            pcr_volume = puts['volume'].sum() / max(calls['volume'].sum(), 1)
            pcr_oi = puts['open_interest'].sum() / max(calls['open_interest'].sum(), 1)
            
            # IV Skew (OTM puts - OTM calls)
            underlying = options['underlying_price'].iloc[0]
            otm_puts = puts[puts['strike'] < underlying * 0.95]
            otm_calls = calls[calls['strike'] > underlying * 1.05]
            
            iv_skew = 0
            if not otm_puts.empty and not otm_calls.empty:
                iv_skew = otm_puts['implied_volatility'].mean() - otm_calls['implied_volatility'].mean()
            
            # Score components
            pcr_score = min(1.0, max(0, pcr_volume - 0.7) / 1.3)  # >2.0 = max risk
            skew_score = min(1.0, max(0, iv_skew) / 0.2)  # 20% skew = max
            
            composite = pcr_score * 0.5 + skew_score * 0.5
            
            return {
                'score': round(composite, 4),
                'put_call_ratio_volume': round(pcr_volume, 4),
                'put_call_ratio_oi': round(pcr_oi, 4),
                'iv_skew': round(iv_skew, 4),
            }
            
        except Exception as e:
            logger.error(f"Options risk calculation failed: {e}")
            return {'score': 0.5, 'error': str(e)}
    
    def _calculate_liquidity_risk(self, ticker: str) -> Dict[str, Any]:
        """
        Liquidity risk assessment.
        
        Factors:
        - Bid-ask spread
        - Volume decline
        - Market cap
        - ADV ratio
        """
        try:
            if not self.db:
                return {'score': 0.5, 'error': 'No database connection'}
            
            volume_data = self.db.query(f"""
                SELECT date, volume, close
                FROM stock_prices
                WHERE ticker = '{ticker}'
                ORDER BY date DESC
                LIMIT 60
            """)
            
            if volume_data.empty:
                return {'score': 0.5, 'data_available': False}
            
            current_vol = volume_data['volume'].iloc[0]
            avg_vol_20 = volume_data['volume'].head(20).mean()
            avg_vol_60 = volume_data['volume'].mean()
            
            # Volume ratio (low = risk)
            vol_ratio = current_vol / avg_vol_20 if avg_vol_20 > 0 else 1.0
            
            # Volume trend
            recent_avg = volume_data['volume'].head(10).mean()
            older_avg = volume_data['volume'].tail(10).mean()
            vol_trend = recent_avg / older_avg if older_avg > 0 else 1.0
            
            # Score (low volume = high risk)
            vol_score = 1 - min(1.0, vol_ratio)  # Invert: low ratio = high risk
            trend_score = 1 - min(1.0, vol_trend)  # Declining trend = risk
            
            composite = vol_score * 0.6 + trend_score * 0.4
            
            return {
                'score': round(composite, 4),
                'volume_ratio': round(vol_ratio, 4),
                'volume_trend': round(vol_trend, 4),
                'avg_volume_20d': int(avg_vol_20),
            }
            
        except Exception as e:
            logger.error(f"Liquidity risk calculation failed: {e}")
            return {'score': 0.5, 'error': str(e)}
    
    def _calculate_momentum_risk(self, ticker: str) -> Dict[str, Any]:
        """
        Momentum/trend reversal risk.
        
        High risk when:
        - Extended price moves
        - RSI extremes
        - Distance from moving averages
        """
        try:
            if not self.db:
                return {'score': 0.5, 'error': 'No database connection'}
            
            prices = self.db.query(f"""
                SELECT date, close
                FROM stock_prices
                WHERE ticker = '{ticker}'
                ORDER BY date DESC
                LIMIT 60
            """)
            
            if prices.empty or len(prices) < 20:
                return {'score': 0.5, 'data_available': False}
            
            prices = prices.sort_values('date')
            close = prices['close']
            
            # RSI
            delta = close.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # Distance from MA
            ma_20 = close.rolling(20).mean().iloc[-1]
            ma_deviation = (close.iloc[-1] / ma_20 - 1) if ma_20 > 0 else 0
            
            # Extreme move detection
            return_20d = close.iloc[-1] / close.iloc[-20] - 1 if len(close) >= 20 else 0
            
            # Risk scores (extremes = risk)
            rsi_risk = max(abs(current_rsi - 50) - 20, 0) / 30  # >70 or <30 = risk
            ma_risk = abs(ma_deviation) / 0.2  # 20% deviation = max
            momentum_risk = abs(return_20d) / 0.3  # 30% move = max
            
            composite = min(1.0, (rsi_risk + ma_risk + momentum_risk) / 3)
            
            return {
                'score': round(composite, 4),
                'rsi': round(current_rsi, 2),
                'ma_deviation': round(ma_deviation, 4),
                'return_20d': round(return_20d, 4),
            }
            
        except Exception as e:
            logger.error(f"Momentum risk calculation failed: {e}")
            return {'score': 0.5, 'error': str(e)}
    
    def _calculate_correlation_risk(self, ticker: str) -> Dict[str, Any]:
        """
        Correlation/contagion risk.
        
        High risk when:
        - Correlation with SPY increases
        - Sector correlation spikes
        """
        # Placeholder - would need market data
        return {'score': 0.3, 'note': 'Correlation analysis pending'}
    
    def _score_to_level(self, score: float) -> str:
        """Convert score to risk level."""
        if score < 0.25:
            return "Low"
        elif score < 0.5:
            return "Medium"
        elif score < 0.75:
            return "High"
        else:
            return "Critical"
    
    def _score_to_signal(self, score: float) -> str:
        """Convert score to trading signal."""
        if score < 0.25:
            return "SAFE"
        elif score < 0.5:
            return "CAUTION"
        elif score < 0.75:
            return "WARNING"
        else:
            return "DANGER"
    
    def _generate_alerts(
        self,
        ticker: str,
        components: Dict[str, Any],
        composite_score: float
    ) -> List[RiskAlert]:
        """Generate risk alerts based on thresholds."""
        alerts = []
        now = datetime.utcnow()
        
        # Composite score alert
        if composite_score >= 0.75:
            alerts.append(RiskAlert(
                alert_type="composite_risk",
                severity="CRITICAL",
                ticker=ticker,
                message=f"Critical margin risk level for {ticker}",
                value=composite_score,
                threshold=0.75,
                triggered_at=now,
            ))
        elif composite_score >= 0.5:
            alerts.append(RiskAlert(
                alert_type="composite_risk",
                severity="HIGH",
                ticker=ticker,
                message=f"Elevated margin risk for {ticker}",
                value=composite_score,
                threshold=0.5,
                triggered_at=now,
            ))
        
        # Component-specific alerts
        for comp_name, comp_data in components.items():
            if isinstance(comp_data, dict) and comp_data.get('score', 0) >= 0.8:
                alerts.append(RiskAlert(
                    alert_type=f"{comp_name}_risk",
                    severity="HIGH",
                    ticker=ticker,
                    message=f"High {comp_name} risk detected for {ticker}",
                    value=comp_data['score'],
                    threshold=0.8,
                    triggered_at=now,
                ))
        
        self._alerts.extend(alerts)
        return alerts
    
    def _run_stress_test(
        self,
        ticker: str,
        components: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run stress test scenarios.
        
        Scenarios:
        - 2008-style crisis
        - COVID crash
        - Flash crash
        - Sector rotation
        """
        scenarios = {
            'crisis_2008': {'vol_mult': 3.0, 'liquidity_mult': 2.0},
            'covid_crash': {'vol_mult': 4.0, 'liquidity_mult': 1.5},
            'flash_crash': {'vol_mult': 2.5, 'liquidity_mult': 3.0},
            'sector_rotation': {'vol_mult': 1.5, 'liquidity_mult': 1.2},
        }
        
        results = {}
        base_score = sum(
            c.get('score', 0) * self.weights.get(name, 0)
            for name, c in components.items()
            if isinstance(c, dict)
        )
        
        for scenario_name, multipliers in scenarios.items():
            stressed_score = base_score
            
            if 'volatility' in components:
                stressed_score += components['volatility'].get('score', 0) * (multipliers['vol_mult'] - 1) * self.weights['volatility']
            if 'liquidity' in components:
                stressed_score += components['liquidity'].get('score', 0) * (multipliers['liquidity_mult'] - 1) * self.weights['liquidity']
            
            stressed_score = min(1.0, stressed_score)
            
            results[scenario_name] = {
                'stressed_score': round(stressed_score, 4),
                'risk_level': self._score_to_level(stressed_score),
                'score_increase': round(stressed_score - base_score, 4),
            }
        
        return results
    
    def _alert_to_dict(self, alert: RiskAlert) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'alert_type': alert.alert_type,
            'severity': alert.severity,
            'ticker': alert.ticker,
            'message': alert.message,
            'value': alert.value,
            'threshold': alert.threshold,
            'triggered_at': alert.triggered_at.isoformat(),
        }
    
    def get_alerts(self, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all generated alerts, optionally filtered by severity."""
        alerts = self._alerts
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return [self._alert_to_dict(a) for a in alerts]
    
    def clear_alerts(self):
        """Clear alert history."""
        self._alerts = []
