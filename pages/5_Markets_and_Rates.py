import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from core.chart_utils import (
    plot_fred_series, display_metric, load_fred_batch,
    get_value_from_batch, get_yoy_from_batch,
)

st.set_page_config(page_title="Markets & Interest Rates", page_icon="📈", layout="wide")

st.title("📈 Financial Markets & Interest Rates")
st.markdown("Analysis of interest rates, yield curves, monetary policy, and financial market indicators")

# ── Load ALL series for this page in one cached batch call ──────────────────
ALL_SERIES = {
    'FEDFUNDS': 'FEDFUNDS',
    'DGS10': 'DGS10',
    'DGS2': 'DGS2',
    'DGS3MO': 'DGS3MO',
    'DGS5': 'DGS5',
    'DGS30': 'DGS30',
    'T10Y2Y': 'T10Y2Y',
    'M2SL': 'M2SL',
    'DPRIME': 'DPRIME',
}
data = load_fred_batch(ALL_SERIES)

# === INTEREST RATE METRICS ===
st.header("💹 Key Interest Rates")

col1, col2, col3, col4 = st.columns(4)

with col1:
    display_metric("Federal Funds Rate",
                   get_value_from_batch(data, 'FEDFUNDS'),
                   fmt="{:.2f}", suffix="%")

with col2:
    display_metric("10-Year Treasury Yield",
                   get_value_from_batch(data, 'DGS10'),
                   fmt="{:.2f}", suffix="%")

with col3:
    display_metric("2-Year Treasury Yield",
                   get_value_from_batch(data, 'DGS2'),
                   fmt="{:.2f}", suffix="%")

with col4:
    spread = get_value_from_batch(data, 'T10Y2Y')
    display_metric("10Y-2Y Yield Spread", spread,
                   fmt="{:.2f}", suffix="%",
                   delta_suffix="",
                   delta=None)
    if spread is not None:
        st.caption("Inverted" if spread < 0 else "Normal")

# === MONETARY POLICY & MONEY SUPPLY ===
st.header("🏛️ Monetary Policy Indicators")

col1, col2, col3, col4 = st.columns(4)

with col1:
    m2 = get_value_from_batch(data, 'M2SL')
    display_metric("M2 Money Supply",
                   m2 if m2 is None else m2 / 1000,
                   fmt="{:.2f}", prefix="$", suffix="T",
                   delta=get_yoy_from_batch(data, 'M2SL'),
                   delta_fmt="{:+.1f}", delta_suffix="% YoY")

with col2:
    display_metric("Bank Prime Loan Rate",
                   get_value_from_batch(data, 'DPRIME'),
                   fmt="{:.2f}", suffix="%")

with col3:
    display_metric("3-Month Treasury Bill",
                   get_value_from_batch(data, 'DGS3MO'),
                   fmt="{:.2f}", suffix="%")

with col4:
    display_metric("5-Year Treasury Yield",
                   get_value_from_batch(data, 'DGS5'),
                   fmt="{:.2f}", suffix="%")

# === YIELD CURVE ANALYSIS ===
st.header("📊 Treasury Yield Curve")

try:
    treasury_3m_val = get_value_from_batch(data, 'DGS3MO')
    treasury_2y_val = get_value_from_batch(data, 'DGS2')
    treasury_5y_val = get_value_from_batch(data, 'DGS5')
    treasury_10y_val = get_value_from_batch(data, 'DGS10')
    treasury_30y_val = get_value_from_batch(data, 'DGS30')

    if all(v is not None for v in [treasury_3m_val, treasury_2y_val, treasury_5y_val, treasury_10y_val, treasury_30y_val]):
        yield_curve_df = pd.DataFrame({
            'Maturity': ['3-Month', '2-Year', '5-Year', '10-Year', '30-Year'],
            'Yield': [treasury_3m_val, treasury_2y_val, treasury_5y_val, treasury_10y_val, treasury_30y_val],
            'Months': [3/12, 2, 5, 10, 30]
        })

        fig = px.line(
            yield_curve_df, x='Months', y='Yield',
            title='Current U.S. Treasury Yield Curve',
            labels={'Months': 'Maturity (Years)', 'Yield': 'Yield (%)'},
            markers=True
        )
        fig.update_layout(template='plotly_dark', hovermode='x unified', height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Insufficient data to create yield curve visualization")
except Exception as e:
    st.warning(f"Unable to create yield curve: {str(e)}")

# === INTEREST RATE TRENDS ===
st.header("📈 Interest Rate Trends")

col1, col2 = st.columns(2)

with col1:
    plot_fred_series('FEDFUNDS', 'Federal Funds Rate (10-Year History)',
                     'Percent', data=data)

with col2:
    plot_fred_series('DGS10', '10-Year Treasury Yield (10-Year History)',
                     'Percent', data=data)

# === YIELD SPREAD TRACKING ===
st.header("📉 Yield Spread Analysis (Recession Indicator)")

col1, col2 = st.columns(2)

with col1:
    # Custom chart with horizontal inversion threshold line
    if data is not None and 'T10Y2Y' in data.columns:
        spread_series = data['T10Y2Y'].dropna()
        if not spread_series.empty:
            fig = px.line(
                spread_series, x=spread_series.index, y='T10Y2Y',
                title='10-Year minus 2-Year Treasury Spread (10-Year History)',
                labels={'T10Y2Y': 'Percentage Points', 'DATE': 'Date'}
            )
            fig.add_hline(y=0, line_dash="dash", line_color="red",
                          annotation_text="Inversion Threshold")
            fig.update_layout(template='plotly_dark', hovermode='x unified', height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Yield spread data not available")
    else:
        st.warning("Yield spread data not available")

with col2:
    plot_fred_series('DGS2', '2-Year Treasury Yield (10-Year History)',
                     'Percent', data=data)

# === MONEY SUPPLY TRENDS ===
st.header("💰 Money Supply Growth")

col1, col2 = st.columns(2)

with col1:
    plot_fred_series('M2SL', 'M2 Money Supply (10-Year History)',
                     'Billions of Dollars', data=data)

with col2:
    plot_fred_series('DPRIME', 'Bank Prime Loan Rate (10-Year History)',
                     'Percent', data=data)

# === FOOTER ===
st.markdown("---")
st.markdown("""
**Policy & Short-Term Rates:**
- **FEDFUNDS**: Federal Funds Effective Rate (Target Policy Rate)
- **DGS3MO**: 3-Month Treasury Bill (Secondary Market Rate)
- **DPRIME**: Bank Prime Loan Rate (Commercial Lending Benchmark)

**Treasury Yield Curve:**
- **DGS2**: 2-Year Treasury Constant Maturity Rate
- **DGS5**: 5-Year Treasury Constant Maturity Rate
- **DGS10**: 10-Year Treasury Constant Maturity Rate
- **DGS30**: 30-Year Treasury Constant Maturity Rate
- **T10Y2Y**: 10-Year minus 2-Year Treasury Spread (Recession Indicator)

**Money Supply:**
- **M2SL**: M2 Money Stock (Currency + Deposits + Money Market Funds)

*Data Source: Federal Reserve Economic Data (FRED)*
""")
