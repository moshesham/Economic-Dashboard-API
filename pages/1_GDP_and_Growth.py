import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from core.chart_utils import (
    plot_fred_series, display_metric, load_fred_batch,
    get_value_from_batch, get_yoy_from_batch,
)

st.set_page_config(page_title="GDP & Growth", page_icon="📊", layout="wide")

st.title("📊 GDP & Economic Growth")
st.markdown("Analysis of US economic growth, GDP components, productivity, and business cycles")

# ── Load ALL series for this page in one cached batch call ──────────────────
ALL_SERIES = {
    'GDP': 'GDP',
    'GDPC1': 'GDPC1',
    'A191RL1Q225SBEA': 'A191RL1Q225SBEA',
    'A939RX0Q048SBEA': 'A939RX0Q048SBEA',
    'PCE': 'PCE',
    'GPDIC1': 'GPDIC1',
    'GCEC1': 'GCEC1',
    'NETEXP': 'NETEXP',
    'OPHNFB': 'OPHNFB',
    'PNFI': 'PNFI',
}
data = load_fred_batch(ALL_SERIES)

# === GDP METRICS ===
st.header("🇺🇸 GDP & Output Metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    gdp = get_value_from_batch(data, 'GDP')
    gdp_yoy = get_yoy_from_batch(data, 'GDP')
    display_metric("Nominal GDP", gdp if gdp is None else gdp / 1000,
                   fmt="{:.2f}", prefix="$", suffix="T",
                   delta=gdp_yoy, delta_fmt="{:+.1f}", delta_suffix="% YoY")

with col2:
    real_gdp = get_value_from_batch(data, 'GDPC1')
    real_gdp_yoy = get_yoy_from_batch(data, 'GDPC1')
    display_metric("Real GDP (Chained 2017 $)", real_gdp if real_gdp is None else real_gdp / 1000,
                   fmt="{:.2f}", prefix="$", suffix="T",
                   delta=real_gdp_yoy, delta_fmt="{:+.1f}", delta_suffix="% YoY")

with col3:
    gdp_growth = get_value_from_batch(data, 'A191RL1Q225SBEA')
    display_metric("Real GDP Growth (QoQ SAAR)", gdp_growth, fmt="{:.1f}", suffix="%")

with col4:
    gdp_pc = get_value_from_batch(data, 'A939RX0Q048SBEA')
    gdp_pc_yoy = get_yoy_from_batch(data, 'A939RX0Q048SBEA')
    display_metric("Real GDP per Capita", gdp_pc, fmt="{:,.0f}", prefix="$",
                   delta=gdp_pc_yoy, delta_fmt="{:+.1f}", delta_suffix="% YoY")

# === GDP COMPONENTS ===
st.header("🧩 GDP Components")

col1, col2, col3, col4 = st.columns(4)

with col1:
    v = get_value_from_batch(data, 'PCE')
    display_metric("Consumption (PCE)", v if v is None else v / 1000,
                   fmt="{:.2f}", prefix="$", suffix="T")

with col2:
    v = get_value_from_batch(data, 'GPDIC1')
    display_metric("Gross Private Investment", v if v is None else v / 1000,
                   fmt="{:.2f}", prefix="$", suffix="T")

with col3:
    v = get_value_from_batch(data, 'GCEC1')
    display_metric("Gov Consumption & Investment", v if v is None else v / 1000,
                   fmt="{:.2f}", prefix="$", suffix="T")

with col4:
    v = get_value_from_batch(data, 'NETEXP')
    display_metric("Net Exports", v if v is None else v / 1000,
                   fmt="{:.2f}", prefix="$", suffix="T")

# === GDP GROWTH TRENDS ===
st.header("📈 GDP Growth Trends")
plot_fred_series('A191RL1Q225SBEA', 'Real GDP Growth Rate (QoQ SAAR)', 'Percent', data=data)

# === REAL GDP & PER CAPITA ===
st.header("💵 Real GDP & Per Capita Trends")

col1, col2 = st.columns(2)

with col1:
    plot_fred_series('GDPC1', 'Real GDP (Chained 2017 Dollars)',
                     'Billions of Chained 2017 Dollars', data=data)

with col2:
    plot_fred_series('A939RX0Q048SBEA', 'Real GDP per Capita (Chained 2017 Dollars)',
                     'Dollars', data=data)

# === PRODUCTIVITY & BUSINESS CYCLES ===
st.header("⚙️ Productivity & Business Cycles")

col1, col2 = st.columns(2)

with col1:
    prod = get_value_from_batch(data, 'OPHNFB')
    prod_yoy = get_yoy_from_batch(data, 'OPHNFB')
    display_metric("Nonfarm Business Productivity", prod, fmt="{:.1f}",
                   delta=prod_yoy, delta_fmt="{:+.1f}", delta_suffix="% YoY")
    plot_fred_series('OPHNFB', 'Nonfarm Business Productivity', 'Index 2012=100', data=data)

with col2:
    inv = get_value_from_batch(data, 'PNFI')
    inv_yoy = get_yoy_from_batch(data, 'PNFI')
    display_metric("Private Nonresidential Fixed Investment",
                   inv if inv is None else inv / 1000,
                   fmt="{:.2f}", prefix="$", suffix="T",
                   delta=inv_yoy, delta_fmt="{:+.1f}", delta_suffix="% YoY")
    plot_fred_series('PNFI', 'Private Nonresidential Fixed Investment',
                     'Billions of Dollars', data=data)
