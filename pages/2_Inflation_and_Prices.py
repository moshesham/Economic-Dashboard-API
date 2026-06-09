"""
Inflation and Prices Analysis
Track inflation metrics, consumer prices, and producer prices.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from core.chart_utils import (
    plot_fred_series, display_metric, load_fred_batch,
    get_value_from_batch, get_yoy_from_batch,
)

try:
    from modules.database import get_bls_data
    BLS_DB_AVAILABLE = True
except Exception:
    BLS_DB_AVAILABLE = False

try:
    from modules.bls_data import refresh_bls_data
    BLS_REFRESH_AVAILABLE = True
except Exception:
    BLS_REFRESH_AVAILABLE = False

from modules.features.wage_inflation_signal import (
    build_wage_inflation_pass_through_features,
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

BLS_PASS_THROUGH_SERIES = [
    'CES0500000003',
    'CES0500000007',
    'CIS2010000000000I',
    'PRS85006093',
]


@st.cache_data(ttl=3600)
def load_bls_pass_through_source(series_ids: list[str], years_back: int = 20) -> pd.DataFrame:
    """Load BLS series needed for pass-through features from local database."""
    if not BLS_DB_AVAILABLE:
        return pd.DataFrame()
    start_date = f"{datetime.now().year - years_back}-01-01"
    df = get_bls_data(series_ids=series_ids, start_date=start_date)
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.dropna(subset=['date', 'series_id', 'value'])
    if df.empty:
        return pd.DataFrame()

    return (
        df.sort_values('date')
          .drop_duplicates(subset=['series_id', 'date'], keep='last')
          .pivot(index='date', columns='series_id', values='value')
          .sort_index()
    )


@st.cache_data(ttl=3600)
def load_wage_pass_through_features(bls_df: pd.DataFrame, inflation_df: pd.DataFrame) -> pd.DataFrame:
    """Build pass-through engineered features with caching."""
    if bls_df is None or bls_df.empty or inflation_df is None or inflation_df.empty:
        return pd.DataFrame()

    inflation_subset = inflation_df[[col for col in ['CPILFESL', 'PPIFGS'] if col in inflation_df.columns]].copy()
    return build_wage_inflation_pass_through_features(bls_df, inflation_subset)


bls_pass_through_data = load_bls_pass_through_source(BLS_PASS_THROUGH_SERIES)
wage_pass_through_df = load_wage_pass_through_features(bls_pass_through_data, data)

with st.sidebar:
    st.divider()
    st.subheader("Pass-Through Data")
    if st.button("Refresh BLS Inputs", type="secondary", disabled=not BLS_REFRESH_AVAILABLE):
        if not BLS_REFRESH_AVAILABLE:
            st.warning("BLS refresh module not available in this runtime.")
        else:
            with st.spinner("Refreshing BLS inputs for pass-through..."):
                try:
                    records = refresh_bls_data(series_ids=BLS_PASS_THROUGH_SERIES)
                    load_bls_pass_through_source.clear()
                    load_wage_pass_through_features.clear()
                    st.success(f"Refreshed BLS source data: {records} rows inserted.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"BLS input refresh failed: {exc}")

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

# === WAGE-INFLATION PASS-THROUGH SIGNAL ===
st.divider()
st.header("🧠 Wage-Inflation Pass-Through Signal")

if wage_pass_through_df.empty:
    st.info("Pass-through features unavailable: load BLS inputs first using the sidebar refresh control.")
else:
    latest = wage_pass_through_df.dropna(how='all').iloc[-1] if not wage_pass_through_df.dropna(how='all').empty else None

    c1, c2, c3 = st.columns(3)
    with c1:
        v = latest.get('unit_labor_cost_proxy') if latest is not None else None
        yoy = latest.get('ulc_proxy_yoy') if latest is not None else None
        display_metric(
            "Unit Labor Cost Proxy",
            v,
            fmt="{:.2f}",
            delta=yoy,
            delta_fmt="{:+.2f}",
            delta_suffix="% YoY",
        )

    with c2:
        v = latest.get('wage_minus_productivity_accel') if latest is not None else None
        display_metric(
            "Wage Accel - Productivity Accel",
            v,
            fmt="{:+.2f}",
            suffix=" pp",
        )

    with c3:
        v = latest.get('corr_wage_pressure_core_cpi_fwd_6m') if latest is not None else None
        display_metric(
            "Forward Corr (6m, Core CPI)",
            v,
            fmt="{:+.2f}",
        )

    left, right = st.columns(2)

    with left:
        fig = go.Figure()
        for col, label, color in [
            ('wage_pressure_composite', 'Wage Pressure Composite', '#FF6B6B'),
            ('core_cpi_yoy', 'Core CPI YoY', '#4ECDC4'),
            ('ppi_yoy', 'PPI YoY', '#FFA94D'),
        ]:
            if col in wage_pass_through_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=wage_pass_through_df.index,
                        y=wage_pass_through_df[col],
                        mode='lines',
                        name=label,
                        line=dict(width=2, color=color),
                    )
                )
        fig.update_layout(
            title='Pass-Through Composite vs Inflation',
            xaxis_title='Date',
            yaxis_title='Percent / Composite Units',
            template='plotly_dark',
            height=380,
            hovermode='x unified',
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        fig = go.Figure()
        corr_cols = [
            ('corr_wage_pressure_core_cpi_fwd_3m', 'Core CPI fwd 3m', '#5DADE2'),
            ('corr_wage_pressure_core_cpi_fwd_6m', 'Core CPI fwd 6m', '#2E86C1'),
            ('corr_wage_pressure_core_cpi_fwd_12m', 'Core CPI fwd 12m', '#1B4F72'),
            ('corr_wage_pressure_ppi_fwd_3m', 'PPI fwd 3m', '#58D68D'),
            ('corr_wage_pressure_ppi_fwd_6m', 'PPI fwd 6m', '#28B463'),
            ('corr_wage_pressure_ppi_fwd_12m', 'PPI fwd 12m', '#145A32'),
        ]
        for col, label, color in corr_cols:
            if col in wage_pass_through_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=wage_pass_through_df.index,
                        y=wage_pass_through_df[col],
                        mode='lines',
                        name=label,
                        line=dict(width=2, color=color),
                    )
                )
        fig.update_layout(
            title='Forward Correlation Features',
            xaxis_title='Date',
            yaxis_title='Rolling Correlation',
            template='plotly_dark',
            height=380,
            hovermode='x unified',
        )
        st.plotly_chart(fig, use_container_width=True)

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

Pass-through section combines BLS wage/productivity series with core CPI/PPI inflation series.
""")
