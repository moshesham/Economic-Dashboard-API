"""
Portfolio endpoints - Optimization and analysis.
"""

from fastapi import APIRouter, Query, HTTPException, Body
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class PortfolioPosition(BaseModel):
    """Single portfolio position."""
    ticker: str = Field(..., description="Stock ticker symbol")
    weight: float = Field(..., ge=0, le=1, description="Portfolio weight (0-1)")


class PortfolioRequest(BaseModel):
    """Portfolio optimization request."""
    tickers: List[str] = Field(..., min_length=2, description="List of ticker symbols")
    target_return: Optional[float] = Field(None, description="Target annual return")
    max_volatility: Optional[float] = Field(None, description="Maximum portfolio volatility")
    risk_free_rate: float = Field(0.05, description="Risk-free rate for Sharpe calculation")
    constraints: Optional[dict] = Field(None, description="Additional constraints")


class RebalanceRequest(BaseModel):
    """Portfolio rebalancing request."""
    current_positions: List[PortfolioPosition] = Field(..., description="Current positions")
    target_weights: List[PortfolioPosition] = Field(..., description="Target weights")
    cash: float = Field(0, description="Available cash for rebalancing")
    min_trade_value: float = Field(100, description="Minimum trade value")


# ============================================================================
# Portfolio Optimization Endpoints
# ============================================================================

@router.post("/optimize")
async def optimize_portfolio(
    request: PortfolioRequest = Body(...),
):
    """
    Optimize portfolio allocation using Mean-Variance Optimization.
    
    Supports multiple optimization objectives:
    - Maximum Sharpe Ratio
    - Minimum Volatility
    - Target Return
    - Risk Parity
    
    Args:
        request: Portfolio optimization parameters
    
    Returns:
        Optimal portfolio weights and metrics
    """
    try:
        import numpy as np
        import pandas as pd
        from scipy.optimize import minimize
        from modules.database import get_db_connection
        
        tickers = [t.upper() for t in request.tickers]
        
        # Fetch historical returns
        db = get_db_connection()
        returns_data = {}
        
        for ticker in tickers:
            result = db.query(f"""
                SELECT date, close
                FROM stock_prices
                WHERE ticker = '{ticker}'
                ORDER BY date DESC
                LIMIT 252
            """)
            if not result.empty:
                returns_data[ticker] = result.set_index('date')['close'].pct_change().dropna()
        
        if len(returns_data) < 2:
            raise HTTPException(
                status_code=400,
                detail="Insufficient data for optimization"
            )
        
        # Create returns DataFrame
        returns_df = pd.DataFrame(returns_data)
        returns_df = returns_df.dropna()
        
        # Calculate expected returns and covariance
        mean_returns = returns_df.mean() * 252  # Annualize
        cov_matrix = returns_df.cov() * 252  # Annualize
        
        n_assets = len(tickers)
        
        # Optimization functions
        def portfolio_volatility(weights):
            return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        
        def portfolio_return(weights):
            return np.dot(weights, mean_returns)
        
        def neg_sharpe_ratio(weights):
            ret = portfolio_return(weights)
            vol = portfolio_volatility(weights)
            return -(ret - request.risk_free_rate) / vol
        
        # Constraints
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
        
        if request.target_return:
            constraints.append({
                'type': 'eq',
                'fun': lambda w: portfolio_return(w) - request.target_return
            })
        
        if request.max_volatility:
            constraints.append({
                'type': 'ineq',
                'fun': lambda w: request.max_volatility - portfolio_volatility(w)
            })
        
        # Bounds (0 to 1 for each asset)
        bounds = tuple((0, 1) for _ in range(n_assets))
        
        # Initial guess (equal weight)
        init_weights = np.array([1/n_assets] * n_assets)
        
        # Optimize
        result = minimize(
            neg_sharpe_ratio,
            init_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        optimal_weights = result.x
        
        # Calculate portfolio metrics
        port_return = portfolio_return(optimal_weights)
        port_volatility = portfolio_volatility(optimal_weights)
        sharpe_ratio = (port_return - request.risk_free_rate) / port_volatility
        
        return {
            "optimization_status": "success" if result.success else "partial",
            "optimal_weights": {
                ticker: round(weight, 4)
                for ticker, weight in zip(tickers, optimal_weights)
            },
            "metrics": {
                "expected_return": round(port_return, 4),
                "volatility": round(port_volatility, 4),
                "sharpe_ratio": round(sharpe_ratio, 4),
            },
            "individual_stats": {
                ticker: {
                    "expected_return": round(mean_returns[ticker], 4),
                    "volatility": round(np.sqrt(cov_matrix[ticker][ticker]), 4),
                }
                for ticker in tickers if ticker in mean_returns
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/efficient-frontier")
async def get_efficient_frontier(
    request: PortfolioRequest = Body(...),
    n_points: int = Query(50, description="Number of points on frontier"),
):
    """
    Calculate the efficient frontier for given assets.
    
    Returns multiple optimal portfolios along the frontier,
    from minimum volatility to maximum return.
    
    Args:
        request: Portfolio tickers
        n_points: Number of points on frontier
    
    Returns:
        Efficient frontier portfolios
    """
    try:
        import numpy as np
        import pandas as pd
        from scipy.optimize import minimize
        from modules.database import get_db_connection
        
        tickers = [t.upper() for t in request.tickers]
        
        # Fetch historical returns (similar to optimize)
        db = get_db_connection()
        returns_data = {}
        
        for ticker in tickers:
            result = db.query(f"""
                SELECT date, close
                FROM stock_prices
                WHERE ticker = '{ticker}'
                ORDER BY date DESC
                LIMIT 252
            """)
            if not result.empty:
                returns_data[ticker] = result.set_index('date')['close'].pct_change().dropna()
        
        returns_df = pd.DataFrame(returns_data).dropna()
        mean_returns = returns_df.mean() * 252
        cov_matrix = returns_df.cov() * 252
        
        n_assets = len(tickers)
        
        def portfolio_volatility(weights):
            return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        
        def portfolio_return(weights):
            return np.dot(weights, mean_returns)
        
        # Calculate min and max returns
        min_return = mean_returns.min()
        max_return = mean_returns.max()
        target_returns = np.linspace(min_return, max_return, n_points)
        
        frontier = []
        bounds = tuple((0, 1) for _ in range(n_assets))
        init_weights = np.array([1/n_assets] * n_assets)
        
        for target in target_returns:
            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
                {'type': 'eq', 'fun': lambda w, t=target: portfolio_return(w) - t}
            ]
            
            result = minimize(
                portfolio_volatility,
                init_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )
            
            if result.success:
                frontier.append({
                    "return": round(target, 4),
                    "volatility": round(result.fun, 4),
                    "sharpe": round((target - request.risk_free_rate) / result.fun, 4),
                    "weights": {t: round(w, 4) for t, w in zip(tickers, result.x)},
                })
        
        # Find special portfolios
        max_sharpe_idx = max(range(len(frontier)), key=lambda i: frontier[i]["sharpe"])
        min_vol_idx = min(range(len(frontier)), key=lambda i: frontier[i]["volatility"])
        
        return {
            "frontier": frontier,
            "special_portfolios": {
                "max_sharpe": frontier[max_sharpe_idx],
                "min_volatility": frontier[min_vol_idx],
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Portfolio Analysis Endpoints
# ============================================================================

@router.post("/analyze")
async def analyze_portfolio(
    positions: List[PortfolioPosition] = Body(...),
):
    """
    Analyze current portfolio risk and composition.
    
    Returns:
    - Sector breakdown
    - Risk metrics (VaR, CVaR, Beta)
    - Concentration metrics
    - Correlation analysis
    
    Args:
        positions: Current portfolio positions
    
    Returns:
        Portfolio analysis results
    """
    try:
        import numpy as np
        import pandas as pd
        from modules.database import get_db_connection
        
        tickers = [p.ticker.upper() for p in positions]
        weights = np.array([p.weight for p in positions])
        
        # Validate weights
        if not np.isclose(weights.sum(), 1.0, atol=0.01):
            raise HTTPException(
                status_code=400,
                detail="Weights must sum to 1.0"
            )
        
        db = get_db_connection()
        returns_data = {}
        
        for ticker in tickers:
            result = db.query(f"""
                SELECT date, close
                FROM stock_prices
                WHERE ticker = '{ticker}'
                ORDER BY date DESC
                LIMIT 252
            """)
            if not result.empty:
                returns_data[ticker] = result.set_index('date')['close'].pct_change().dropna()
        
        returns_df = pd.DataFrame(returns_data).dropna()
        
        # Portfolio returns
        portfolio_returns = returns_df.dot(weights)
        
        # Risk metrics
        daily_vol = portfolio_returns.std()
        annual_vol = daily_vol * np.sqrt(252)
        
        # VaR (95%)
        var_95 = np.percentile(portfolio_returns, 5)
        
        # CVaR (Expected Shortfall)
        cvar_95 = portfolio_returns[portfolio_returns <= var_95].mean()
        
        # Maximum Drawdown
        cumulative = (1 + portfolio_returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdowns = cumulative / running_max - 1
        max_drawdown = drawdowns.min()
        
        # Concentration (HHI)
        hhi = np.sum(weights ** 2)
        
        # Correlation matrix
        corr_matrix = returns_df.corr()
        
        return {
            "risk_metrics": {
                "annual_volatility": round(annual_vol, 4),
                "daily_volatility": round(daily_vol, 4),
                "var_95_daily": round(var_95, 4),
                "cvar_95_daily": round(cvar_95, 4),
                "max_drawdown": round(max_drawdown, 4),
            },
            "concentration": {
                "hhi": round(hhi, 4),
                "effective_n": round(1 / hhi, 2),  # Effective number of stocks
            },
            "correlation": corr_matrix.to_dict(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rebalance")
async def calculate_rebalance_trades(
    request: RebalanceRequest = Body(...),
):
    """
    Calculate trades needed to rebalance portfolio.
    
    Args:
        request: Current and target positions
    
    Returns:
        List of trades needed
    """
    try:
        current = {p.ticker.upper(): p.weight for p in request.current_positions}
        target = {p.ticker.upper(): p.weight for p in request.target_weights}
        
        all_tickers = set(current.keys()) | set(target.keys())
        
        trades = []
        for ticker in all_tickers:
            curr_weight = current.get(ticker, 0)
            tgt_weight = target.get(ticker, 0)
            diff = tgt_weight - curr_weight
            
            if abs(diff) > 0.001:  # 0.1% threshold
                trades.append({
                    "ticker": ticker,
                    "current_weight": curr_weight,
                    "target_weight": tgt_weight,
                    "weight_change": round(diff, 4),
                    "action": "BUY" if diff > 0 else "SELL",
                })
        
        # Sort by absolute change (largest first)
        trades.sort(key=lambda x: abs(x["weight_change"]), reverse=True)
        
        return {
            "trades": trades,
            "trade_count": len(trades),
            "buy_count": sum(1 for t in trades if t["action"] == "BUY"),
            "sell_count": sum(1 for t in trades if t["action"] == "SELL"),
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Risk Parity
# ============================================================================

@router.post("/risk-parity")
async def calculate_risk_parity(
    request: PortfolioRequest = Body(...),
):
    """
    Calculate Risk Parity portfolio weights.
    
    Each asset contributes equally to total portfolio risk.
    
    Args:
        request: Portfolio tickers
    
    Returns:
        Risk parity weights
    """
    try:
        import numpy as np
        import pandas as pd
        from scipy.optimize import minimize
        from modules.database import get_db_connection
        
        tickers = [t.upper() for t in request.tickers]
        db = get_db_connection()
        returns_data = {}
        
        for ticker in tickers:
            result = db.query(f"""
                SELECT date, close
                FROM stock_prices
                WHERE ticker = '{ticker}'
                ORDER BY date DESC
                LIMIT 252
            """)
            if not result.empty:
                returns_data[ticker] = result.set_index('date')['close'].pct_change().dropna()
        
        returns_df = pd.DataFrame(returns_data).dropna()
        cov_matrix = returns_df.cov() * 252
        
        n_assets = len(tickers)
        
        def risk_contribution(weights):
            port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            marginal_contrib = np.dot(cov_matrix, weights) / port_vol
            risk_contrib = weights * marginal_contrib
            return risk_contrib
        
        def risk_parity_objective(weights):
            risk_contribs = risk_contribution(weights)
            target_contrib = 1 / n_assets
            return np.sum((risk_contribs - target_contrib) ** 2)
        
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
        bounds = tuple((0.01, 0.99) for _ in range(n_assets))
        init_weights = np.array([1/n_assets] * n_assets)
        
        result = minimize(
            risk_parity_objective,
            init_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        final_weights = result.x
        risk_contribs = risk_contribution(final_weights)
        port_vol = np.sqrt(np.dot(final_weights.T, np.dot(cov_matrix, final_weights)))
        
        return {
            "weights": {t: round(w, 4) for t, w in zip(tickers, final_weights)},
            "risk_contributions": {t: round(rc, 4) for t, rc in zip(tickers, risk_contribs)},
            "portfolio_volatility": round(port_vol, 4),
            "optimization_success": result.success,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
