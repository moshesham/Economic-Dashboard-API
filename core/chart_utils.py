"""
Reusable chart and metric display utilities for Streamlit dashboard pages.

Eliminates duplication of chart generation, metric display, and data loading
patterns that were repeated 40+ times across dashboard pages.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional


def plot_fred_series(
    series_id: str,
    title: str,
    ylabel: str,
    data: Optional[pd.DataFrame] = None,
    height: int = 400,
    chart_type: str = "line",
    color: Optional[str] = None,
) -> None:
    """
    Plot a single FRED series with standard dark theme styling.

    Args:
        series_id: FRED series ID (used as column name in data).
        title: Chart title.
        ylabel: Y-axis label.
        data: Pre-loaded DataFrame. If None, loads via load_fred_data.
        height: Chart height in pixels.
        chart_type: 'line' or 'bar'.
        color: Optional line/bar color.
    """
    if data is None:
        from modules.data_loader import load_fred_data
        data = load_fred_data({series_id: series_id})

    if data is None or data.empty:
        st.warning(f"{title} — data not available")
        return

    col_name = series_id if series_id in data.columns else data.columns[0]

    if chart_type == "bar":
        fig = px.bar(
            data, x=data.index, y=col_name,
            title=title, labels={col_name: ylabel, "DATE": "Date"},
            color_discrete_sequence=[color] if color else None,
        )
    else:
        fig = px.line(
            data, x=data.index, y=col_name,
            title=title, labels={col_name: ylabel, "DATE": "Date"},
            color_discrete_sequence=[color] if color else None,
        )

    fig.update_layout(template="plotly_dark", hovermode="x unified", height=height)
    st.plotly_chart(fig, use_container_width=True)


def display_metric(
    label: str,
    value,
    fmt: str = "{:.2f}",
    prefix: str = "",
    suffix: str = "",
    delta=None,
    delta_fmt: str = "{:+.1f}%",
    delta_suffix: str = "",
    delta_color: str = "normal",
    help_text: Optional[str] = None,
) -> None:
    """
    Display a Streamlit metric with safe None handling.

    Args:
        label: Metric label.
        value: Numeric value (None-safe).
        fmt: Format string for the value.
        prefix: Text before the formatted value (e.g. '$').
        suffix: Text after the formatted value (e.g. '%', 'M').
        delta: Optional delta value.
        delta_fmt: Format string for delta.
        delta_suffix: Suffix for delta display.
        delta_color: 'normal', 'inverse', or 'off'.
        help_text: Optional tooltip.
    """
    display_value = f"{prefix}{fmt.format(value)}{suffix}" if value is not None else "N/A"
    display_delta = (
        f"{delta_fmt.format(delta)}{delta_suffix}" if delta is not None else None
    )

    st.metric(
        label=label,
        value=display_value,
        delta=display_delta,
        delta_color=delta_color,
        help=help_text,
    )


@st.cache_data(ttl=3600)
def load_fred_batch(series_dict: dict) -> pd.DataFrame:
    """
    Load multiple FRED series in a single cached call.

    This is the recommended way to load data for an entire page —
    one call instead of N separate calls, and the result is cached
    for 1 hour via Streamlit's cache.

    Args:
        series_dict: Mapping of descriptive_name → FRED series ID.
                     Pass as a regular dict; Streamlit hashes it.

    Returns:
        DataFrame with DatetimeIndex, one column per series.
    """
    from modules.data_loader import load_fred_data
    return load_fred_data(series_dict)


@st.cache_data(ttl=3600)
def load_yfinance_batch(tickers_dict: dict, period: str = "5y") -> dict:
    """
    Load multiple Yahoo Finance tickers in a single cached call.

    Args:
        tickers_dict: Mapping of descriptive_name → ticker symbol.
        period: Time period to fetch.

    Returns:
        Dictionary of {name: DataFrame}.
    """
    from modules.data_loader import load_yfinance_data
    return load_yfinance_data(tickers_dict, period)


def get_value_from_batch(data: pd.DataFrame, column: str):
    """Get the latest non-null value from a batch-loaded DataFrame."""
    if data is None or data.empty or column not in data.columns:
        return None
    series = data[column].dropna()
    return series.iloc[-1] if not series.empty else None


def get_yoy_from_batch(data: pd.DataFrame, column: str):
    """Calculate year-over-year change from a batch-loaded DataFrame."""
    if data is None or data.empty or column not in data.columns:
        return None
    series = data[column].dropna()
    if len(series) < 2:
        return None
    current = series.iloc[-1]
    # Find value approximately 12 months ago
    try:
        target_date = series.index[-1] - pd.DateOffset(years=1)
        idx = series.index.get_indexer([target_date], method="nearest")[0]
        if idx >= 0:
            previous = series.iloc[idx]
            if previous != 0:
                return ((current - previous) / abs(previous)) * 100
    except Exception:
        pass
    return None
