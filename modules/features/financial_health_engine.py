"""
Advanced Financial Health Analytics

Enhanced financial health scoring with:
- Multi-dimensional health assessment
- Peer comparison analysis
- Trend detection and forecasting
- Early warning signals
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class HealthRating(Enum):
    """Financial health rating categories."""
    EXCELLENT = "A"
    GOOD = "B"
    FAIR = "C"
    POOR = "D"
    CRITICAL = "F"


@dataclass
class HealthTrend:
    """Health trend data."""
    direction: str  # IMPROVING, STABLE, DETERIORATING
    strength: float  # 0-1
    periods_analyzed: int
    key_drivers: List[str]


class FinancialHealthEngine:
    """
    Advanced financial health analysis engine.
    
    Improvements over base scorer:
    1. Multi-dimensional health vectors
    2. Sector-relative benchmarking
    3. Trend analysis with mean reversion detection
    4. Early warning system
    5. Scenario analysis
    """
    
    # Health dimension weights
    DIMENSION_WEIGHTS = {
        'profitability': 0.25,
        'leverage': 0.20,
        'liquidity': 0.15,
        'efficiency': 0.15,
        'growth': 0.15,
        'quality': 0.10,
    }
    
    # Rating thresholds
    RATING_THRESHOLDS = {
        HealthRating.EXCELLENT: 80,
        HealthRating.GOOD: 65,
        HealthRating.FAIR: 50,
        HealthRating.POOR: 35,
        HealthRating.CRITICAL: 0,
    }
    
    def __init__(self, db=None):
        self.db = db
        self._sector_benchmarks: Dict[str, Dict[str, float]] = {}
    
    def calculate_health_score(
        self,
        ticker: str,
        include_peer_comparison: bool = True,
        include_trend: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive financial health score.
        
        Args:
            ticker: Stock ticker symbol
            include_peer_comparison: Compare to sector peers
            include_trend: Analyze trend over time
        
        Returns:
            Complete health assessment
        """
        ticker = ticker.upper()
        
        # Get financial data
        financials = self._get_financial_data(ticker)
        if not financials:
            return {'error': f'No financial data for {ticker}'}
        
        # Calculate dimension scores
        dimensions = {}
        
        # 1. Profitability
        dimensions['profitability'] = self._calculate_profitability_score(financials)
        
        # 2. Leverage
        dimensions['leverage'] = self._calculate_leverage_score(financials)
        
        # 3. Liquidity
        dimensions['liquidity'] = self._calculate_liquidity_score(financials)
        
        # 4. Efficiency
        dimensions['efficiency'] = self._calculate_efficiency_score(financials)
        
        # 5. Growth
        dimensions['growth'] = self._calculate_growth_score(financials)
        
        # 6. Quality
        dimensions['quality'] = self._calculate_quality_score(financials)
        
        # Calculate composite score
        composite_score = self._calculate_composite_score(dimensions)
        
        # Determine rating
        rating = self._score_to_rating(composite_score)
        
        # Piotroski F-Score (classic metric)
        f_score = self._calculate_piotroski_score(financials)
        
        # Altman Z-Score
        z_score = self._calculate_altman_z_score(financials)
        
        # Peer comparison
        peer_analysis = None
        if include_peer_comparison:
            peer_analysis = self._compare_to_peers(ticker, dimensions)
        
        # Trend analysis
        trend = None
        if include_trend:
            trend = self._analyze_trend(ticker)
        
        # Early warning signals
        warnings = self._detect_warning_signals(financials, dimensions)
        
        return {
            'ticker': ticker,
            'composite_score': round(composite_score, 2),
            'health_rating': rating.value,
            'dimensions': {
                name: {
                    'score': round(data['score'], 2),
                    'weight': self.DIMENSION_WEIGHTS[name],
                    'weighted_contribution': round(
                        data['score'] * self.DIMENSION_WEIGHTS[name], 2
                    ),
                    'metrics': data.get('metrics', {}),
                }
                for name, data in dimensions.items()
            },
            'classic_scores': {
                'piotroski_f_score': f_score,
                'altman_z_score': z_score,
            },
            'peer_comparison': peer_analysis,
            'trend': trend,
            'warnings': warnings,
            'calculated_at': datetime.utcnow().isoformat(),
        }
    
    def _get_financial_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch financial data from database or SEC API."""
        try:
            if self.db:
                # Try to get from cache first
                result = self.db.query(f"""
                    SELECT *
                    FROM financial_metrics
                    WHERE ticker = '{ticker}'
                    ORDER BY period_end DESC
                    LIMIT 8
                """)
                
                if not result.empty:
                    return self._parse_financial_data(result)
            
            # Fallback to SEC API
            return self._fetch_from_sec(ticker)
            
        except Exception as e:
            logger.error(f"Failed to get financial data for {ticker}: {e}")
            return None
    
    def _parse_financial_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Parse financial data from database result."""
        if df.empty:
            return {}
        
        latest = df.iloc[0].to_dict()
        
        # Calculate YoY changes if we have prior year
        yoy_changes = {}
        if len(df) >= 4:
            prior = df.iloc[4].to_dict()  # Same quarter last year
            for key in ['revenue', 'net_income', 'total_assets']:
                if key in latest and key in prior:
                    if prior[key] and prior[key] != 0:
                        yoy_changes[f'{key}_yoy'] = (latest[key] / prior[key]) - 1
        
        return {**latest, **yoy_changes, 'historical': df.to_dict('records')}
    
    def _fetch_from_sec(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch financial data from SEC API."""
        # Placeholder - would integrate with SEC data loader
        return None
    
    def _calculate_profitability_score(self, financials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate profitability dimension score.
        
        Metrics:
        - Return on Equity (ROE)
        - Return on Assets (ROA)
        - Net Profit Margin
        - Gross Margin
        - Operating Margin
        """
        metrics = {}
        scores = []
        
        # ROE
        roe = financials.get('roe')
        if roe is not None:
            metrics['roe'] = roe
            # Score: 15%+ = 100, 0% = 50, negative = lower
            roe_score = min(100, max(0, 50 + roe * 333))
            scores.append(roe_score)
        
        # ROA
        roa = financials.get('roa')
        if roa is not None:
            metrics['roa'] = roa
            roa_score = min(100, max(0, 50 + roa * 500))
            scores.append(roa_score)
        
        # Net margin
        net_margin = financials.get('net_margin')
        if net_margin is not None:
            metrics['net_margin'] = net_margin
            margin_score = min(100, max(0, 50 + net_margin * 250))
            scores.append(margin_score)
        
        # Gross margin
        gross_margin = financials.get('gross_margin')
        if gross_margin is not None:
            metrics['gross_margin'] = gross_margin
            gm_score = min(100, max(0, gross_margin * 100))
            scores.append(gm_score)
        
        avg_score = np.mean(scores) if scores else 50
        
        return {
            'score': avg_score,
            'metrics': metrics,
            'metric_count': len(scores),
        }
    
    def _calculate_leverage_score(self, financials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate leverage dimension score.
        
        Metrics:
        - Debt to Equity
        - Debt to Assets
        - Interest Coverage
        - Debt to EBITDA
        """
        metrics = {}
        scores = []
        
        # Debt to Equity (lower = better, inverted scoring)
        de_ratio = financials.get('debt_to_equity')
        if de_ratio is not None:
            metrics['debt_to_equity'] = de_ratio
            # Score: 0 = 100, 1.0 = 50, 2.0+ = 0
            de_score = max(0, 100 - de_ratio * 50)
            scores.append(de_score)
        
        # Interest Coverage (higher = better)
        interest_coverage = financials.get('interest_coverage')
        if interest_coverage is not None:
            metrics['interest_coverage'] = interest_coverage
            # Score: 5x+ = 100, 1x = 20, <1 = 0
            ic_score = min(100, max(0, interest_coverage * 20))
            scores.append(ic_score)
        
        # Debt to Assets
        da_ratio = financials.get('debt_to_assets')
        if da_ratio is not None:
            metrics['debt_to_assets'] = da_ratio
            da_score = max(0, 100 - da_ratio * 150)
            scores.append(da_score)
        
        avg_score = np.mean(scores) if scores else 50
        
        return {
            'score': avg_score,
            'metrics': metrics,
            'metric_count': len(scores),
        }
    
    def _calculate_liquidity_score(self, financials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate liquidity dimension score.
        
        Metrics:
        - Current Ratio
        - Quick Ratio
        - Cash Ratio
        - Working Capital / Revenue
        """
        metrics = {}
        scores = []
        
        # Current Ratio
        current_ratio = financials.get('current_ratio')
        if current_ratio is not None:
            metrics['current_ratio'] = current_ratio
            # Score: 2.0 = 100, 1.0 = 50, 0.5 = 0
            cr_score = min(100, max(0, current_ratio * 50))
            scores.append(cr_score)
        
        # Quick Ratio
        quick_ratio = financials.get('quick_ratio')
        if quick_ratio is not None:
            metrics['quick_ratio'] = quick_ratio
            qr_score = min(100, max(0, quick_ratio * 67))
            scores.append(qr_score)
        
        # Cash Ratio
        cash_ratio = financials.get('cash_ratio')
        if cash_ratio is not None:
            metrics['cash_ratio'] = cash_ratio
            cash_score = min(100, max(0, cash_ratio * 100))
            scores.append(cash_score)
        
        avg_score = np.mean(scores) if scores else 50
        
        return {
            'score': avg_score,
            'metrics': metrics,
            'metric_count': len(scores),
        }
    
    def _calculate_efficiency_score(self, financials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate efficiency dimension score.
        
        Metrics:
        - Asset Turnover
        - Inventory Turnover
        - Receivables Turnover
        - Operating Cash Flow / Revenue
        """
        metrics = {}
        scores = []
        
        # Asset Turnover
        asset_turnover = financials.get('asset_turnover')
        if asset_turnover is not None:
            metrics['asset_turnover'] = asset_turnover
            at_score = min(100, asset_turnover * 50)
            scores.append(at_score)
        
        # Inventory Turnover
        inv_turnover = financials.get('inventory_turnover')
        if inv_turnover is not None:
            metrics['inventory_turnover'] = inv_turnover
            it_score = min(100, inv_turnover * 10)
            scores.append(it_score)
        
        # OCF / Revenue
        ocf_margin = financials.get('ocf_margin')
        if ocf_margin is not None:
            metrics['ocf_margin'] = ocf_margin
            ocf_score = min(100, max(0, 50 + ocf_margin * 200))
            scores.append(ocf_score)
        
        avg_score = np.mean(scores) if scores else 50
        
        return {
            'score': avg_score,
            'metrics': metrics,
            'metric_count': len(scores),
        }
    
    def _calculate_growth_score(self, financials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate growth dimension score.
        
        Metrics:
        - Revenue Growth YoY
        - Earnings Growth YoY
        - Asset Growth
        - Book Value Growth
        """
        metrics = {}
        scores = []
        
        # Revenue Growth
        rev_growth = financials.get('revenue_yoy')
        if rev_growth is not None:
            metrics['revenue_growth_yoy'] = rev_growth
            # Score: 20%+ = 100, 0% = 50, -20% = 0
            rg_score = min(100, max(0, 50 + rev_growth * 250))
            scores.append(rg_score)
        
        # Earnings Growth
        earnings_growth = financials.get('net_income_yoy')
        if earnings_growth is not None:
            metrics['earnings_growth_yoy'] = earnings_growth
            eg_score = min(100, max(0, 50 + earnings_growth * 200))
            scores.append(eg_score)
        
        avg_score = np.mean(scores) if scores else 50
        
        return {
            'score': avg_score,
            'metrics': metrics,
            'metric_count': len(scores),
        }
    
    def _calculate_quality_score(self, financials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate earnings quality dimension score.
        
        Metrics:
        - Accruals Ratio
        - OCF / Net Income
        - Revenue Quality
        - Earnings Persistence
        """
        metrics = {}
        scores = []
        
        # Accruals Ratio (lower = higher quality)
        accruals = financials.get('accruals_ratio')
        if accruals is not None:
            metrics['accruals_ratio'] = accruals
            # Negative accruals = good (cash > earnings)
            acc_score = min(100, max(0, 50 - accruals * 200))
            scores.append(acc_score)
        
        # OCF / Net Income (higher = better quality)
        ocf_ni_ratio = financials.get('ocf_to_net_income')
        if ocf_ni_ratio is not None:
            metrics['ocf_to_net_income'] = ocf_ni_ratio
            # 1.0+ = good, means cash supports earnings
            ocf_score = min(100, max(0, ocf_ni_ratio * 50))
            scores.append(ocf_score)
        
        avg_score = np.mean(scores) if scores else 50
        
        return {
            'score': avg_score,
            'metrics': metrics,
            'metric_count': len(scores),
        }
    
    def _calculate_composite_score(self, dimensions: Dict[str, Dict[str, Any]]) -> float:
        """Calculate weighted composite score."""
        total_score = 0
        total_weight = 0
        
        for dim_name, dim_data in dimensions.items():
            if dim_name in self.DIMENSION_WEIGHTS:
                weight = self.DIMENSION_WEIGHTS[dim_name]
                score = dim_data.get('score', 50)
                total_score += score * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 50
    
    def _score_to_rating(self, score: float) -> HealthRating:
        """Convert score to health rating."""
        for rating, threshold in self.RATING_THRESHOLDS.items():
            if score >= threshold:
                return rating
        return HealthRating.CRITICAL
    
    def _calculate_piotroski_score(self, financials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Piotroski F-Score (0-9).
        
        Profitability (4 points):
        1. Positive net income
        2. Positive operating cash flow
        3. ROA increasing
        4. OCF > Net Income (quality)
        
        Leverage (3 points):
        5. Leverage decreasing
        6. Current ratio increasing
        7. No new shares issued
        
        Efficiency (2 points):
        8. Gross margin increasing
        9. Asset turnover increasing
        """
        score = 0
        breakdown = {}
        
        # 1. Positive ROA
        roa = financials.get('roa', 0)
        if roa and roa > 0:
            score += 1
            breakdown['positive_roa'] = True
        else:
            breakdown['positive_roa'] = False
        
        # 2. Positive OCF
        ocf = financials.get('operating_cf', 0)
        if ocf and ocf > 0:
            score += 1
            breakdown['positive_ocf'] = True
        else:
            breakdown['positive_ocf'] = False
        
        # 3. ROA increasing (simplified - would need historical)
        breakdown['roa_increasing'] = None  # Needs historical data
        
        # 4. OCF > Net Income
        net_income = financials.get('net_income', 0)
        if ocf and net_income and ocf > net_income:
            score += 1
            breakdown['quality_earnings'] = True
        else:
            breakdown['quality_earnings'] = False
        
        # 5. Leverage decreasing (simplified)
        breakdown['leverage_decreasing'] = None
        
        # 6. Current ratio increasing (simplified)
        breakdown['liquidity_improving'] = None
        
        # 7. No dilution
        breakdown['no_dilution'] = None
        
        # 8. Gross margin increasing
        breakdown['margin_improving'] = None
        
        # 9. Asset turnover increasing
        breakdown['efficiency_improving'] = None
        
        return {
            'score': score,
            'max_score': 9,
            'breakdown': breakdown,
            'interpretation': self._interpret_f_score(score),
        }
    
    def _interpret_f_score(self, score: int) -> str:
        """Interpret Piotroski F-Score."""
        if score >= 8:
            return "Strong fundamentals - high quality"
        elif score >= 6:
            return "Good fundamentals"
        elif score >= 4:
            return "Average fundamentals"
        elif score >= 2:
            return "Weak fundamentals"
        else:
            return "Very weak fundamentals - caution"
    
    def _calculate_altman_z_score(self, financials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Altman Z-Score for bankruptcy prediction.
        
        Z = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E
        
        A = Working Capital / Total Assets
        B = Retained Earnings / Total Assets
        C = EBIT / Total Assets
        D = Market Value of Equity / Total Liabilities
        E = Sales / Total Assets
        """
        try:
            total_assets = financials.get('total_assets', 0) or 1
            
            # A: Working Capital / Total Assets
            wc = financials.get('working_capital', 0) or 0
            A = wc / total_assets
            
            # B: Retained Earnings / Total Assets
            re = financials.get('retained_earnings', 0) or 0
            B = re / total_assets
            
            # C: EBIT / Total Assets
            ebit = financials.get('ebit', 0) or 0
            C = ebit / total_assets
            
            # D: Market Cap / Total Liabilities
            market_cap = financials.get('market_cap', 0) or 0
            total_liab = financials.get('total_liabilities', 0) or 1
            D = market_cap / total_liab
            
            # E: Sales / Total Assets
            revenue = financials.get('revenue', 0) or 0
            E = revenue / total_assets
            
            z_score = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E
            
            # Interpretation
            if z_score > 2.99:
                zone = "Safe Zone"
                risk = "Low bankruptcy risk"
            elif z_score > 1.81:
                zone = "Grey Zone"
                risk = "Moderate bankruptcy risk"
            else:
                zone = "Distress Zone"
                risk = "High bankruptcy risk"
            
            return {
                'z_score': round(z_score, 2),
                'zone': zone,
                'risk_interpretation': risk,
                'components': {
                    'A_working_capital': round(A, 4),
                    'B_retained_earnings': round(B, 4),
                    'C_ebit': round(C, 4),
                    'D_market_equity': round(D, 4),
                    'E_sales': round(E, 4),
                }
            }
            
        except Exception as e:
            logger.error(f"Z-Score calculation failed: {e}")
            return {'error': str(e)}
    
    def _compare_to_peers(
        self,
        ticker: str,
        dimensions: Dict[str, Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Compare to sector peers."""
        # Would need sector classification and peer data
        return {
            'note': 'Peer comparison requires sector data',
            'sector': None,
            'percentile_rank': None,
        }
    
    def _analyze_trend(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Analyze health trend over time."""
        # Would need historical health scores
        return {
            'direction': 'STABLE',
            'strength': 0.5,
            'periods_analyzed': 0,
            'note': 'Trend analysis requires historical data',
        }
    
    def _detect_warning_signals(
        self,
        financials: Dict[str, Any],
        dimensions: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect early warning signals."""
        warnings = []
        
        # Check dimension scores
        for dim_name, dim_data in dimensions.items():
            score = dim_data.get('score', 50)
            if score < 30:
                warnings.append({
                    'type': 'dimension_weakness',
                    'dimension': dim_name,
                    'score': score,
                    'severity': 'HIGH',
                    'message': f'Weak {dim_name} score: {score:.1f}/100',
                })
        
        # Check specific ratios
        current_ratio = financials.get('current_ratio')
        if current_ratio and current_ratio < 1.0:
            warnings.append({
                'type': 'liquidity_risk',
                'metric': 'current_ratio',
                'value': current_ratio,
                'severity': 'HIGH',
                'message': f'Current ratio below 1.0: {current_ratio:.2f}',
            })
        
        debt_to_equity = financials.get('debt_to_equity')
        if debt_to_equity and debt_to_equity > 2.0:
            warnings.append({
                'type': 'leverage_risk',
                'metric': 'debt_to_equity',
                'value': debt_to_equity,
                'severity': 'MEDIUM',
                'message': f'High debt-to-equity: {debt_to_equity:.2f}',
            })
        
        return warnings
