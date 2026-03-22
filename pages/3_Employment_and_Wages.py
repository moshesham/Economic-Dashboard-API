import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from core.chart_utils import (
    plot_fred_series, display_metric, load_fred_batch,
    get_value_from_batch, get_yoy_from_batch,
)

st.set_page_config(page_title="Employment & Wages", page_icon="💼", layout="wide")

st.title("💼 Employment & Wages Analysis")
st.markdown("Comprehensive analysis of US labor market conditions, employment trends, and wage growth")

# ── Load ALL series for this page in one cached batch call ──────────────────
ALL_SERIES = {
    'UNRATE': 'UNRATE',
    'PAYEMS': 'PAYEMS',
    'CIVPART': 'CIVPART',
    'EMRATIO': 'EMRATIO',
    'CES0500000003': 'CES0500000003',
    'AHETPI': 'AHETPI',
    'ICSA': 'ICSA',
    'CCSA': 'CCSA',
}
data = load_fred_batch(ALL_SERIES)

# === HEADLINE METRICS ===
st.header("📊 Key Employment Metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    v = get_value_from_batch(data, 'UNRATE')
    yoy = get_yoy_from_batch(data, 'UNRATE')
    display_metric("Unemployment Rate", v, fmt="{:.1f}", suffix="%",
                   delta=yoy, delta_fmt="{:+.1f}", delta_suffix="pp", delta_color="inverse")

with col2:
    v = get_value_from_batch(data, 'PAYEMS')
    yoy = get_yoy_from_batch(data, 'PAYEMS')
    display_metric("Total Nonfarm Payrolls", v if v is None else v / 1000,
                   fmt="{:.1f}", suffix="M",
                   delta=yoy, delta_fmt="{:+.1f}", delta_suffix="%")

with col3:
    v = get_value_from_batch(data, 'CIVPART')
    yoy = get_yoy_from_batch(data, 'CIVPART')
    display_metric("Labor Force Participation", v, fmt="{:.1f}", suffix="%",
                   delta=yoy, delta_fmt="{:+.1f}", delta_suffix="pp")

with col4:
    v = get_value_from_batch(data, 'EMRATIO')
    yoy = get_yoy_from_batch(data, 'EMRATIO')
    display_metric("Employment-Population Ratio", v, fmt="{:.1f}", suffix="%",
                   delta=yoy, delta_fmt="{:+.1f}", delta_suffix="pp")

# === WAGE METRICS ===
st.header("💰 Wage & Earnings Trends")

col1, col2, col3, col4 = st.columns(4)

with col1:
    v = get_value_from_batch(data, 'CES0500000003')
    yoy = get_yoy_from_batch(data, 'CES0500000003')
    display_metric("Avg Hourly Earnings (Private)", v, fmt="{:.2f}", prefix="$",
                   delta=yoy, delta_fmt="{:+.1f}", delta_suffix="% YoY")

with col2:
    v = get_value_from_batch(data, 'AHETPI')
    yoy = get_yoy_from_batch(data, 'AHETPI')
    display_metric("Real Avg Hourly Earnings", v, fmt="{:.2f}", prefix="$",
                   delta=yoy, delta_fmt="{:+.1f}", delta_suffix="% YoY")

with col3:
    v = get_value_from_batch(data, 'ICSA')
    yoy = get_yoy_from_batch(data, 'ICSA')
    display_metric("Initial Jobless Claims", v if v is None else v / 1000,
                   fmt="{:.0f}", suffix="K",
                   delta=yoy, delta_fmt="{:+.1f}", delta_suffix="%", delta_color="inverse")

with col4:
    v = get_value_from_batch(data, 'CCSA')
    yoy = get_yoy_from_batch(data, 'CCSA')
    display_metric("Continued Jobless Claims", v if v is None else v / 1000,
                   fmt="{:.0f}", suffix="K",
                   delta=yoy, delta_fmt="{:+.1f}", delta_suffix="%", delta_color="inverse")

# === UNEMPLOYMENT TRENDS ===
st.header("📈 Unemployment Rate Trends")

if data is not None and not data.empty and 'UNRATE' in data.columns:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data.index, y=data['UNRATE'],
        name='Unemployment Rate', line=dict(color='#FF6B6B', width=2), mode='lines'
    ))
    if len(data) >= 6:
        ma6 = data['UNRATE'].rolling(window=6).mean()
        fig.add_trace(go.Scatter(
            x=data.index, y=ma6,
            name='6-Month MA', line=dict(color='#4ECDC4', width=2, dash='dash'), mode='lines'
        ))
    fig.update_layout(
        title='Unemployment Rate (Monthly)', xaxis_title='Date',
        yaxis_title='Unemployment Rate (%)', template='plotly_dark',
        hovermode='x unified', height=400,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Unemployment rate data not available")

# === EMPLOYMENT GROWTH ===
st.header("📊 Payroll Employment Growth")

col1, col2 = st.columns(2)

with col1:
    plot_fred_series('PAYEMS', 'Total Nonfarm Payrolls', 'Thousands of Employees', data=data)

with col2:
    plot_fred_series('CIVPART', 'Labor Force Participation Rate', 'Participation Rate (%)', data=data)

# === WAGE GROWTH ANALYSIS ===
st.header("💵 Real vs Nominal Wage Growth")

col1, col2 = st.columns(2)

with col1:
    plot_fred_series('CES0500000003', 'Average Hourly Earnings - Nominal', 'Dollars per Hour', data=data)

with col2:
    plot_fred_series('AHETPI', 'Average Hourly Earnings - Real', '1982-84 Dollars per Hour', data=data)

# === JOBLESS CLAIMS TRACKING ===
st.header("📉 Jobless Claims Trends")

col1, col2 = st.columns(2)

with col1:
    plot_fred_series('ICSA', 'Initial Jobless Claims', 'Thousands of Claims', data=data)

with col2:
    plot_fred_series('CCSA', 'Continued Jobless Claims', 'Thousands of Claims', data=data)

# === FOOTER ===
st.markdown("---")
st.markdown("""
**Data Series Tracked:**
- **UNRATE**: Unemployment Rate
- **PAYEMS**: Total Nonfarm Payrolls
- **CIVPART**: Labor Force Participation Rate
- **EMRATIO**: Employment-Population Ratio
- **CES0500000003**: Average Hourly Earnings (Private Sector)
- **AHETPI**: Real Average Hourly Earnings (Production & Nonsupervisory)
- **ICSA**: Initial Jobless Claims (Weekly)
- **CCSA**: Continued Jobless Claims (Insured Unemployment)

*Data Source: Federal Reserve Economic Data (FRED)*
""")
