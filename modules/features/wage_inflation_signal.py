"""Wage-inflation pass-through signal engineering.

Builds signal features from wage, labor cost, productivity, and inflation series:
- Unit labor cost proxy from wages adjusted by productivity
- Wage acceleration minus productivity acceleration
- Forward-correlation features to future inflation horizons
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Iterable


REQUIRED_BLS_COLUMNS = {
    "CES0500000003",  # Average Hourly Earnings
    "CES0500000007",  # Average Weekly Hours
    "CIS2010000000000I",  # Employment Cost Index
    "PRS85006093",  # Labor Productivity Index
}

REQUIRED_INFLATION_COLUMNS = {
    "CPILFESL",  # Core CPI
    "PPIFGS",  # Producer Price Index: Final Goods
}


def _annualized_forward_return(series: pd.Series, horizon_months: int) -> pd.Series:
    """Annualized forward percentage change over a monthly horizon."""
    ratio = series.shift(-horizon_months) / series
    # Convert horizon return into annualized rate to normalize across horizons.
    return (np.power(ratio, 12.0 / horizon_months) - 1.0) * 100.0


def build_wage_inflation_pass_through_features(
    bls_df: pd.DataFrame,
    inflation_df: pd.DataFrame,
    horizons: Iterable[int] = (3, 6, 12),
    rolling_window: int = 24,
) -> pd.DataFrame:
    """Build wage-inflation pass-through features indexed by monthly date.

    Args:
        bls_df: DataFrame indexed by date with BLS columns in REQUIRED_BLS_COLUMNS.
        inflation_df: DataFrame indexed by date with inflation columns in REQUIRED_INFLATION_COLUMNS.
        horizons: Forward inflation horizons in months.
        rolling_window: Rolling window for forward-correlation features.

    Returns:
        DataFrame with engineered signal features.
    """
    if bls_df is None or inflation_df is None or bls_df.empty or inflation_df.empty:
        return pd.DataFrame()

    missing_bls = REQUIRED_BLS_COLUMNS.difference(bls_df.columns)
    missing_inf = REQUIRED_INFLATION_COLUMNS.difference(inflation_df.columns)
    if missing_bls or missing_inf:
        return pd.DataFrame()

    base = pd.DataFrame(index=pd.to_datetime(bls_df.index))
    base = base.sort_index()

    merged = base.join(
        bls_df[list(REQUIRED_BLS_COLUMNS)].copy(),
        how="left",
    ).join(
        inflation_df[list(REQUIRED_INFLATION_COLUMNS)].copy(),
        how="left",
    ).sort_index()

    # Forward-fill monthly macro prints; these are low-frequency and frequently ragged.
    merged = merged.ffill()

    # 1) Unit labor cost proxy: hourly earnings * hours, adjusted by productivity.
    # Normalize by productivity index level to represent labor cost pressure per output unit.
    merged["weekly_labor_cost_proxy"] = (
        merged["CES0500000003"] * merged["CES0500000007"]
    )
    merged["unit_labor_cost_proxy"] = (
        merged["weekly_labor_cost_proxy"] / merged["PRS85006093"]
    ) * 100.0

    # Growth rates (YoY) for wage and productivity pressure decomposition.
    merged["ahe_yoy"] = merged["CES0500000003"].pct_change(12) * 100.0
    merged["eci_yoy"] = merged["CIS2010000000000I"].pct_change(12) * 100.0
    merged["productivity_yoy"] = merged["PRS85006093"].pct_change(12) * 100.0
    merged["ulc_proxy_yoy"] = merged["unit_labor_cost_proxy"].pct_change(12) * 100.0

    # 2) Wage acceleration minus productivity acceleration.
    merged["wage_acceleration"] = merged["ahe_yoy"].diff(3)
    merged["productivity_acceleration"] = merged["productivity_yoy"].diff(3)
    merged["wage_minus_productivity_accel"] = (
        merged["wage_acceleration"] - merged["productivity_acceleration"]
    )

    # Combine wage pressure channels into one composite feature for correlation studies.
    merged["wage_pressure_composite"] = (
        0.5 * merged["ulc_proxy_yoy"]
        + 0.3 * (merged["ahe_yoy"] - merged["productivity_yoy"])
        + 0.2 * merged["wage_minus_productivity_accel"]
    )

    # Inflation YoY references for direct dashboard interpretation.
    merged["core_cpi_yoy"] = merged["CPILFESL"].pct_change(12) * 100.0
    merged["ppi_yoy"] = merged["PPIFGS"].pct_change(12) * 100.0

    # 3) Forward-correlation features to inflation horizons.
    for h in horizons:
        if h <= 0:
            continue
        cpi_forward = _annualized_forward_return(merged["CPILFESL"], h)
        ppi_forward = _annualized_forward_return(merged["PPIFGS"], h)

        merged[f"core_cpi_fwd_{h}m_ann"] = cpi_forward
        merged[f"ppi_fwd_{h}m_ann"] = ppi_forward

        merged[f"corr_wage_pressure_core_cpi_fwd_{h}m"] = (
            merged["wage_pressure_composite"].rolling(rolling_window).corr(cpi_forward)
        )
        merged[f"corr_wage_pressure_ppi_fwd_{h}m"] = (
            merged["wage_pressure_composite"].rolling(rolling_window).corr(ppi_forward)
        )

    return merged
