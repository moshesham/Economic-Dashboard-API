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

BLS_SERIES_IDS = [
    'LNS14000000',  # U-3
    'LNS13327709',  # U-6
    'LNS12300000',  # LFPR aggregate
    'LNS11300060',  # LFPR prime-age 25-54
    'JTS000000000000000JOL',
    'JTS000000000000000QUR',
    'CES0500000003',
    'CES0500000007',
    'CIS2010000000000I',
    'PRS85006093',
]


@st.cache_data(ttl=3600)
def load_bls_batch(series_ids: list[str], years_back: int = 15) -> pd.DataFrame:
    """Load BLS data from local database and pivot to date index / series columns."""
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

    pivoted = (
        df.sort_values('date')
          .drop_duplicates(subset=['series_id', 'date'], keep='last')
          .pivot(index='date', columns='series_id', values='value')
          .sort_index()
    )
    return pivoted


def _latest_and_yoy(series_df: pd.DataFrame, series_id: str) -> tuple[float | None, float | None]:
    """Return latest value and approximate YoY percentage change for a BLS series."""
    if series_df.empty or series_id not in series_df.columns:
        return None, None

    s = series_df[series_id].dropna()
    if s.empty:
        return None, None

    latest = float(s.iloc[-1])
    if len(s) < 13:
        return latest, None

    prior = float(s.iloc[-13])
    if prior == 0:
        return latest, None

    yoy = (latest / prior - 1.0) * 100.0
    return latest, yoy


bls_data = load_bls_batch(BLS_SERIES_IDS)

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

# === BLS DIRECT DATA (SLACK & CHURN) ===
st.header("🧭 BLS Labor Slack & Churn (Direct)")

if not bls_data.empty:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        v, yoy = _latest_and_yoy(bls_data, 'LNS14000000')
        display_metric(
            "U-3 Unemployment (BLS)",
            v,
            fmt="{:.1f}",
            suffix="%",
            delta=yoy,
            delta_fmt="{:+.1f}",
            delta_suffix="% YoY",
            delta_color="inverse",
        )

    with col2:
        v, yoy = _latest_and_yoy(bls_data, 'LNS13327709')
        display_metric(
            "U-6 Underemployment (BLS)",
            v,
            fmt="{:.1f}",
            suffix="%",
            delta=yoy,
            delta_fmt="{:+.1f}",
            delta_suffix="% YoY",
            delta_color="inverse",
        )

    with col3:
        v, yoy = _latest_and_yoy(bls_data, 'JTS000000000000000JOL')
        display_metric(
            "JOLTS Openings (BLS)",
            v,
            fmt="{:.0f}",
            suffix="K",
            delta=yoy,
            delta_fmt="{:+.1f}",
            delta_suffix="% YoY",
        )

    with col4:
        v, yoy = _latest_and_yoy(bls_data, 'JTS000000000000000QUR')
        display_metric(
            "JOLTS Quits Rate (BLS)",
            v,
            fmt="{:.2f}",
            suffix="%",
            delta=yoy,
            delta_fmt="{:+.1f}",
            delta_suffix="% YoY",
        )

    left, right = st.columns(2)

    with left:
        fig = go.Figure()
        for sid, label, color in [
            ('LNS14000000', 'U-3', '#FF6B6B'),
            ('LNS13327709', 'U-6', '#FFA94D'),
        ]:
            if sid in bls_data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=bls_data.index,
                        y=bls_data[sid],
                        mode='lines',
                        name=label,
                        line=dict(width=2, color=color),
                    )
                )
        fig.update_layout(
            title='BLS Labor Slack: U-3 vs U-6',
            xaxis_title='Date',
            yaxis_title='Rate (%)',
            template='plotly_dark',
            height=380,
            hovermode='x unified',
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        fig = go.Figure()
        if 'JTS000000000000000JOL' in bls_data.columns:
            fig.add_trace(
                go.Scatter(
                    x=bls_data.index,
                    y=bls_data['JTS000000000000000JOL'],
                    mode='lines',
                    name='Job Openings (K)',
                    line=dict(width=2, color='#4ECDC4'),
                )
            )
        if 'JTS000000000000000QUR' in bls_data.columns:
            fig.add_trace(
                go.Scatter(
                    x=bls_data.index,
                    y=bls_data['JTS000000000000000QUR'],
                    mode='lines',
                    name='Quits Rate (%)',
                    line=dict(width=2, color='#7C4DFF'),
                    yaxis='y2',
                )
            )
        fig.update_layout(
            title='BLS Labor Churn: Openings and Quits',
            xaxis_title='Date',
            yaxis=dict(title='Openings (Thousands)', side='left'),
            yaxis2=dict(title='Quits Rate (%)', side='right', overlaying='y'),
            template='plotly_dark',
            height=380,
            hovermode='x unified',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("BLS direct-series data is not in local database yet. Run BLS refresh to populate bls_data.")

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
