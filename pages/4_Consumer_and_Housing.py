import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from core.chart_utils import (
    plot_fred_series, display_metric, load_fred_batch,
    get_value_from_batch, get_yoy_from_batch,
)

st.set_page_config(page_title="Consumer & Housing", page_icon="🏠", layout="wide")

st.title("🏠 Consumer Spending & Housing Market")
st.markdown("Analysis of consumer behavior, personal spending, savings trends, and housing market dynamics")

# ── Load ALL series for this page in one cached batch call ──────────────────
ALL_SERIES = {
    'PCE': 'PCE',
    'PCEC96': 'PCEC96',
    'PSAVERT': 'PSAVERT',
    'RSXFS': 'RSXFS',
    'HOUST': 'HOUST',
    'CSUSHPISA': 'CSUSHPISA',
    'MORTGAGE30US': 'MORTGAGE30US',
    'HSN1F': 'HSN1F',
}
data = load_fred_batch(ALL_SERIES)

# === CONSUMER SPENDING METRICS ===
st.header("🛒 Consumer Spending & Savings")

col1, col2, col3, col4 = st.columns(4)

with col1:
    pce = get_value_from_batch(data, 'PCE')
    display_metric("Personal Consumption Expenditures",
                   pce if pce is None else pce / 1000,
                   fmt="{:.2f}", prefix="$", suffix="T",
                   delta=get_yoy_from_batch(data, 'PCE'),
                   delta_fmt="{:+.1f}", delta_suffix="% YoY")

with col2:
    real_pce = get_value_from_batch(data, 'PCEC96')
    display_metric("Real PCE (Chained 2017 $)",
                   real_pce if real_pce is None else real_pce / 1000,
                   fmt="{:.2f}", prefix="$", suffix="T",
                   delta=get_yoy_from_batch(data, 'PCEC96'),
                   delta_fmt="{:+.1f}", delta_suffix="% YoY")

with col3:
    display_metric("Personal Saving Rate",
                   get_value_from_batch(data, 'PSAVERT'),
                   fmt="{:.1f}", suffix="%")

with col4:
    display_metric("Retail Sales (ex Food Services)",
                   get_value_from_batch(data, 'RSXFS'),
                   fmt="{:.0f}", prefix="$", suffix="B",
                   delta=get_yoy_from_batch(data, 'RSXFS'),
                   delta_fmt="{:+.1f}", delta_suffix="% YoY")

# === HOUSING MARKET METRICS ===
st.header("🏘️ Housing Market Indicators")

col1, col2, col3, col4 = st.columns(4)

with col1:
    display_metric("Housing Starts",
                   get_value_from_batch(data, 'HOUST'),
                   fmt="{:.0f}", suffix="K",
                   delta=get_yoy_from_batch(data, 'HOUST'),
                   delta_fmt="{:+.1f}", delta_suffix="% YoY")

with col2:
    display_metric("Case-Shiller Home Price Index",
                   get_value_from_batch(data, 'CSUSHPISA'),
                   fmt="{:.1f}",
                   delta=get_yoy_from_batch(data, 'CSUSHPISA'),
                   delta_fmt="{:+.1f}", delta_suffix="% YoY")

with col3:
    display_metric("30-Year Mortgage Rate",
                   get_value_from_batch(data, 'MORTGAGE30US'),
                   fmt="{:.2f}", suffix="%")

with col4:
    display_metric("New Home Sales",
                   get_value_from_batch(data, 'HSN1F'),
                   fmt="{:.0f}", suffix="K",
                   delta=get_yoy_from_batch(data, 'HSN1F'),
                   delta_fmt="{:+.1f}", delta_suffix="% YoY")

# === CONSUMER SPENDING TRENDS ===
st.header("📈 Consumer Spending Trends")

col1, col2 = st.columns(2)

with col1:
    plot_fred_series('PCE', 'Personal Consumption Expenditures (10-Year History)',
                     'Billions of Dollars', data=data)

with col2:
    plot_fred_series('PSAVERT', 'Personal Saving Rate (10-Year History)',
                     'Percent', data=data)

# === REAL VS NOMINAL SPENDING ===
st.header("💵 Real vs Nominal Consumer Spending")

col1, col2 = st.columns(2)

with col1:
    plot_fred_series('PCEC96', 'Real Personal Consumption (Chained 2017 Dollars)',
                     'Billions of Chained 2017 Dollars', data=data)

with col2:
    plot_fred_series('RSXFS', 'Retail Sales ex Food Services (10-Year History)',
                     'Millions of Dollars', data=data)

# === HOUSING MARKET TRENDS ===
st.header("🏡 Housing Market Activity")

col1, col2 = st.columns(2)

with col1:
    plot_fred_series('HOUST', 'Housing Starts (10-Year History)',
                     'Thousands of Units', data=data)

with col2:
    plot_fred_series('CSUSHPISA', 'S&P/Case-Shiller Home Price Index (10-Year History)',
                     'Index (Jan 2000 = 100)', data=data)

# === MORTGAGE RATES & AFFORDABILITY ===
st.header("🏦 Mortgage Rates & Housing Affordability")

col1, col2 = st.columns(2)

with col1:
    plot_fred_series('MORTGAGE30US', '30-Year Fixed Mortgage Rate (10-Year History)',
                     'Percent', data=data)

with col2:
    plot_fred_series('HSN1F', 'New Single-Family Home Sales (10-Year History)',
                     'Thousands of Units', data=data)

# === FOOTER ===
st.markdown("---")
st.markdown("""
**Consumer Spending Series:**
- **PCE**: Personal Consumption Expenditures (Nominal)
- **PCEC96**: Real Personal Consumption Expenditures (Chained 2017 Dollars)
- **PSAVERT**: Personal Saving Rate (% of Disposable Income)
- **RSXFS**: Retail Sales Excluding Food Services

**Housing Market Series:**
- **HOUST**: Housing Starts (New Private Housing Units)
- **CSUSHPISA**: S&P/Case-Shiller U.S. National Home Price Index (Seasonally Adjusted)
- **MORTGAGE30US**: 30-Year Fixed Rate Mortgage Average
- **HSN1F**: New Single-Family Home Sales

*Data Source: Federal Reserve Economic Data (FRED)*
""")
