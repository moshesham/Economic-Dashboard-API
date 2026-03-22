"""
Inflation and Prices Analysis
Track inflation metrics, consumer prices, and producer prices.
"""

import streamlit as st
import pandas as pd
from core.chart_utils import (
    plot_fred_series, display_metric, load_fred_batch,
    get_value_from_batch, get_yoy_from_batch,
)

# Page configuration
st.set_page_config(
    page_title="Inflation & Prices",
    page_icon="💹",
    layout="wide"
)

st.title("💹 Inflation & Prices")
st.markdown("### Track inflation metrics and price indices")

# ── Load ALL series for this page in one cached batch call ──────────────────
ALL_SERIES = {
    'CPIAUCSL': 'CPIAUCSL',
    'CPILFESL': 'CPILFESL',
    'PCEPI': 'PCEPI',
    'PCEPILFE': 'PCEPILFE',
    'PPIFGS': 'PPIFGS',
    'IR': 'IR',
    'T5YIE': 'T5YIE',
    'CPIUFDSL': 'CPIUFDSL',
}
data = load_fred_batch(ALL_SERIES)

# === INFLATION METRICS ===
st.header("Consumer Price Indices")

col1, col2, col3, col4 = st.columns(4)

with col1:
    v = get_value_from_batch(data, 'CPIAUCSL')
    yoy = get_yoy_from_batch(data, 'CPIAUCSL')
    display_metric("CPI (All Urban Consumers)", v, fmt="{:.1f}",
                   delta=yoy, delta_fmt="{:+.1f}", delta_suffix="% YoY")

with col2:
    v = get_value_from_batch(data, 'CPILFESL')
    yoy = get_yoy_from_batch(data, 'CPILFESL')
    display_metric("Core CPI (ex Food & Energy)", v, fmt="{:.1f}",
                   delta=yoy, delta_fmt="{:+.1f}", delta_suffix="% YoY")

with col3:
    v = get_value_from_batch(data, 'PCEPI')
    yoy = get_yoy_from_batch(data, 'PCEPI')
    display_metric("PCE Price Index", v, fmt="{:.1f}",
                   delta=yoy, delta_fmt="{:+.1f}", delta_suffix="% YoY")

with col4:
    v = get_value_from_batch(data, 'PCEPILFE')
    yoy = get_yoy_from_batch(data, 'PCEPILFE')
    display_metric("Core PCE Price Index", v, fmt="{:.1f}",
                   delta=yoy, delta_fmt="{:+.1f}", delta_suffix="% YoY")

# === PRODUCER PRICES & EXPECTATIONS ===
st.divider()
st.header("Producer Prices & Market Expectations")

col1, col2, col3, col4 = st.columns(4)

with col1:
    v = get_value_from_batch(data, 'PPIFGS')
    yoy = get_yoy_from_batch(data, 'PPIFGS')
    display_metric("Producer Price Index (Final Goods)", v, fmt="{:.1f}",
                   delta=yoy, delta_fmt="{:+.1f}", delta_suffix="% YoY")

with col2:
    v = get_value_from_batch(data, 'IR')
    yoy = get_yoy_from_batch(data, 'IR')
    display_metric("Import Price Index", v, fmt="{:.1f}",
                   delta=yoy, delta_fmt="{:+.1f}", delta_suffix="% YoY")

with col3:
    v = get_value_from_batch(data, 'T5YIE')
    display_metric("5-Year Breakeven Inflation", v, fmt="{:.2f}", suffix="%")

with col4:
    v = get_value_from_batch(data, 'CPIUFDSL')
    yoy = get_yoy_from_batch(data, 'CPIUFDSL')
    display_metric("CPI: Food", v, fmt="{:.1f}",
                   delta=yoy, delta_fmt="{:+.1f}", delta_suffix="% YoY")

# === INFLATION TRENDS ===
st.divider()
st.header("Inflation Trends")

col1, col2 = st.columns(2)

with col1:
    plot_fred_series('CPIAUCSL', 'CPI (All Urban Consumers)', 'Index 1982-84=100', data=data)

with col2:
    plot_fred_series('CPILFESL', 'Core CPI (ex Food & Energy)', 'Index 1982-84=100', data=data)

# === PCE & PRODUCER PRICES ===
st.divider()
st.header("PCE & Producer Prices")

col1, col2 = st.columns(2)

with col1:
    plot_fred_series('PCEPI', 'PCE Price Index', 'Index 2012=100', data=data)

with col2:
    plot_fred_series('PPIFGS', 'Producer Price Index: Final Goods', 'Index 1982=100', data=data)

# === INFLATION EXPECTATIONS & IMPORT PRICES ===
st.divider()
st.header("Inflation Expectations & Import Prices")

col1, col2 = st.columns(2)

with col1:
    plot_fred_series('T5YIE', '5-Year Breakeven Inflation Rate', 'Percent', data=data)

with col2:
    plot_fred_series('IR', 'Import Price Index', 'Index 2000=100', data=data)

# === FOOTER ===
st.divider()
st.info("""
**Inflation & Price Series:**
- **CPIAUCSL**: Consumer Price Index (All Urban Consumers)
- **CPILFESL**: Core CPI (ex Food & Energy)
- **PCEPI**: Personal Consumption Expenditures Price Index
- **PCEPILFE**: Core PCE Price Index
- **PPIFGS**: Producer Price Index: Final Goods
- **IR**: Import Price Index
- **T5YIE**: 5-Year Breakeven Inflation Rate (Market-Based Expectation)
- **CPIUFDSL**: CPI: Food

*Data Source: Federal Reserve Economic Data (FRED)*
""")
