"""
US Economic Dashboard - Homepage
Comprehensive view of US economic health and key indicators
"""

import os
import warnings

# Suppress Streamlit warnings when running outside streamlit context
os.environ['STREAMLIT_LOGGER_LEVEL'] = 'error'
warnings.filterwarnings('ignore', message='.*missing ScriptRunContext.*')

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from modules.data_loader import (
    load_fred_data,
    get_latest_value,
    calculate_percentage_change,
    calculate_yoy_change
)
from core.config import is_offline_mode, can_use_offline_data
from modules.auth.credentials_manager import get_credentials_manager
from modules.ingestion import get_incremental_fetcher


DASHBOARD_CATALOG = [
    {
        "name": "GDP and Growth",
        "path": "pages/1_GDP_and_Growth.py",
        "group": "Macro Core",
        "status": "Ready",
        "data_mode": "Offline sample + FRED",
        "blocker": "None",
    },
    {
        "name": "Inflation and Prices",
        "path": "pages/2_Inflation_and_Prices.py",
        "group": "Macro Core",
        "status": "Ready",
        "data_mode": "Offline sample + FRED",
        "blocker": "None",
    },
    {
        "name": "Employment and Wages",
        "path": "pages/3_Employment_and_Wages.py",
        "group": "Macro Core",
        "status": "Ready",
        "data_mode": "Offline sample + FRED",
        "blocker": "None",
    },
    {
        "name": "Consumer and Housing",
        "path": "pages/4_Consumer_and_Housing.py",
        "group": "Macro Core",
        "status": "Ready",
        "data_mode": "Offline sample + FRED",
        "blocker": "None",
    },
    {
        "name": "Markets and Rates",
        "path": "pages/5_Markets_and_Rates.py",
        "group": "Macro Core",
        "status": "Ready",
        "data_mode": "Offline sample + FRED",
        "blocker": "None",
    },
    {
        "name": "Market Indices",
        "path": "pages/7_Market_Indices.py",
        "group": "Market Intelligence",
        "status": "Partial",
        "data_mode": "Local sample + Yahoo Finance",
        "blocker": "Freshness depends on live market API",
    },
    {
        "name": "Stock Technical Analysis",
        "path": "pages/8_Stock_Technical_Analysis.py",
        "group": "Market Intelligence",
        "status": "API Required",
        "data_mode": "Yahoo Finance live",
        "blocker": "Needs live OHLCV coverage for selected tickers",
    },
    {
        "name": "News Sentiment",
        "path": "pages/9_News_Sentiment.py",
        "group": "Market Intelligence",
        "status": "API Required",
        "data_mode": "News + trends live APIs",
        "blocker": "No bundled offline news corpus",
    },
    {
        "name": "Margin Call Risk Monitor",
        "path": "pages/10_Margin_Call_Risk_Monitor.py",
        "group": "Risk and Signals",
        "status": "Partial",
        "data_mode": "PostgreSQL + live volatility feeds",
        "blocker": "Requires initialized local DB and fresh market inputs",
    },
    {
        "name": "Financial Health Scorer",
        "path": "pages/11_Financial_Health_Scorer.py",
        "group": "Risk and Signals",
        "status": "API Required",
        "data_mode": "SEC live APIs",
        "blocker": "No offline SEC filing bundle",
    },
    {
        "name": "Sector Rotation Monitor",
        "path": "pages/12_Sector_Rotation_Monitor.py",
        "group": "Risk and Signals",
        "status": "API Required",
        "data_mode": "Sector ETF live prices",
        "blocker": "Needs broad, fresh sector price coverage",
    },
    {
        "name": "Insider Trading Tracker",
        "path": "pages/13_Insider_Trading_Tracker.py",
        "group": "Risk and Signals",
        "status": "API Required",
        "data_mode": "SEC Form 4 live APIs",
        "blocker": "Depends on SEC access and rate limits",
    },
    {
        "name": "Economic Indicators Deep Dive",
        "path": "pages/14_Economic_Indicators_Deep_Dive.py",
        "group": "Research and ML",
        "status": "Ready",
        "data_mode": "Offline sample + FRED",
        "blocker": "None",
    },
    {
        "name": "SEC Data Explorer",
        "path": "pages/15_SEC_Data_Explorer.py",
        "group": "Research and ML",
        "status": "API Required",
        "data_mode": "SEC live APIs",
        "blocker": "No offline filing data",
    },
    {
        "name": "Recession Probability",
        "path": "pages/16_Recession_Probability.py",
        "group": "Research and ML",
        "status": "Partial",
        "data_mode": "FRED + market + local model artifacts",
        "blocker": "Needs model artifacts and market data freshness",
    },
    {
        "name": "ML Predictions Explorer",
        "path": "pages/17_ML_Predictions_Explorer.py",
        "group": "Research and ML",
        "status": "Partial",
        "data_mode": "Local models + PostgreSQL OHLCV",
        "blocker": "Requires seeded OHLCV and trained models",
    },
    {
        "name": "API Key Management",
        "path": "pages/6_API_Key_Management.py",
        "group": "Admin",
        "status": "Ready",
        "data_mode": "Local configuration only",
        "blocker": "None",
    },
]


def render_navigation_hub() -> None:
    """Render grouped page links for faster exploration."""
    st.markdown('<div class="section-header"><h3>🗂️ Navigation Hub</h3></div>', unsafe_allow_html=True)
    st.caption("Start with Macro Core, then branch into market, risk, and ML workflows.")

    groups = ["Macro Core", "Market Intelligence", "Risk and Signals", "Research and ML", "Admin"]
    tabs = st.tabs(groups)

    for idx, group in enumerate(groups):
        with tabs[idx]:
            for item in DASHBOARD_CATALOG:
                if item["group"] != group:
                    continue
                c1, c2, c3 = st.columns([4, 2, 3])
                c1.page_link(item["path"], label=item["name"], icon="➡️")
                c2.write(f"**{item['status']}**")
                c3.caption(item["data_mode"])


def render_data_readiness_matrix() -> None:
    """Show users what works locally versus what needs API access."""
    st.markdown('<div class="section-header"><h3>✅ Data Readiness Matrix</h3></div>', unsafe_allow_html=True)
    readiness_df = pd.DataFrame(DASHBOARD_CATALOG)[
        ["group", "name", "status", "data_mode", "blocker"]
    ].rename(
        columns={
            "group": "Group",
            "name": "Dashboard",
            "status": "Status",
            "data_mode": "Data Mode",
            "blocker": "Notes",
        }
    )
    st.dataframe(readiness_df, width="stretch", hide_index=True)

# Page configuration
st.set_page_config(
    page_title="Economic Dashboard | Real-Time Financial Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        background: linear-gradient(135deg, #0068c9 0%, #4a00e0 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(0, 104, 201, 0.3);
    }
    
    .main-header h1 {
        color: white !important;
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.5rem !important;
    }
    
    .main-header p {
        color: rgba(255, 255, 255, 0.9) !important;
        font-size: 1.1rem !important;
        margin-bottom: 0 !important;
    }
    
    /* Metric card styling */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #081943 0%, #0a1f4d 100%);
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
    }
    
    [data-testid="stMetric"] label {
        color: rgba(255, 255, 255, 0.7) !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: white !important;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
    }
    
    /* Section headers */
    .section-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid rgba(0, 104, 201, 0.3);
    }
    
    .section-header h3 {
        color: #0068c9 !important;
        font-weight: 600 !important;
        margin: 0 !important;
    }
    
    /* Status badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .status-online {
        background: rgba(0, 200, 83, 0.2);
        color: #00c853;
        border: 1px solid rgba(0, 200, 83, 0.3);
    }
    
    .status-offline {
        background: rgba(255, 152, 0, 0.2);
        color: #ff9800;
        border: 1px solid rgba(255, 152, 0, 0.3);
    }
    
    /* Footer styling */
    .footer {
        text-align: center;
        padding: 2rem 0;
        margin-top: 3rem;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        color: rgba(255, 255, 255, 0.5);
    }
    
    /* Navigation cards */
    .nav-card {
        background: linear-gradient(135deg, #081943 0%, #0a1f4d 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all 0.3s ease;
        height: 100%;
    }
    
    .nav-card:hover {
        border-color: #0068c9;
        box-shadow: 0 4px 20px rgba(0, 104, 201, 0.2);
    }
    
    .nav-card h4 {
        color: #0068c9 !important;
        margin-bottom: 0.5rem !important;
    }
    
    .nav-card p {
        color: rgba(255, 255, 255, 0.7) !important;
        font-size: 0.9rem !important;
        margin: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# Hero Header
st.markdown("""
<div class="main-header">
    <h1>📊 Economic Dashboard</h1>
    <p>Professional-grade real-time insights into the US economy and global markets</p>
</div>
""", unsafe_allow_html=True)

# Status bar with timestamp
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    if is_offline_mode():
        st.markdown('<span class="status-badge status-offline">📴 Offline Mode</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-badge status-online">🟢 Live Data</span>', unsafe_allow_html=True)
with col3:
    st.caption(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}")

st.divider()

# ========== HEADLINE METRICS ==========
st.markdown('<div class="section-header"><h3>🎯 Headline Economic Indicators</h3></div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    try:
        gdp_growth = get_latest_value('A191RL1Q225SBEA')
        if gdp_growth is not None:
            st.metric(
                label="Real GDP Growth",
                value=f"{gdp_growth:.2f}%",
                delta=f"{gdp_growth:.2f}% QoQ",
                help="Quarterly real GDP growth rate (annualized)"
            )
        else:
            st.metric(label="Real GDP Growth", value="N/A")
    except:
        st.metric(label="Real GDP Growth", value="N/A")

with col2:
    try:
        unrate = get_latest_value('UNRATE')
        if unrate is not None:
            st.metric(
                label="Unemployment Rate",
                value=f"{unrate:.1f}%",
                delta_color="inverse",
                help="Civilian unemployment rate"
            )
        else:
            st.metric(label="Unemployment Rate", value="N/A")
    except:
        st.metric(label="Unemployment Rate", value="N/A")

with col3:
    try:
        cpi_yoy = calculate_yoy_change('CPIAUCSL')
        if cpi_yoy is not None:
            st.metric(
                label="Inflation (CPI)",
                value=f"{cpi_yoy:.1f}%",
                delta=f"{cpi_yoy:.1f}% YoY",
                help="Consumer Price Index, year-over-year change"
            )
        else:
            st.metric(label="Inflation (CPI)", value="N/A")
    except:
        st.metric(label="Inflation (CPI)", value="N/A")

with col4:
    try:
        fed_funds = get_latest_value('FEDFUNDS')
        if fed_funds is not None:
            st.metric(
                label="Fed Funds Rate",
                value=f"{fed_funds:.2f}%",
                help="Federal funds effective rate"
            )
        else:
            st.metric(label="Fed Funds Rate", value="N/A")
    except:
        st.metric(label="Fed Funds Rate", value="N/A")

st.divider()

# ========== EMPLOYMENT & WAGES ==========
st.markdown('<div class="section-header"><h3>💼 Employment & Wages</h3></div>', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)

with col1:
    try:
        payems = get_latest_value('PAYEMS')
        if payems is not None:
            st.metric(
                label="Total Nonfarm Payrolls",
                value=f"{payems/1000:.1f}M",
                help="Total employed in thousands"
            )
        else:
            st.metric(label="Total Nonfarm Payrolls", value="N/A")
    except:
        st.metric(label="Total Nonfarm Payrolls", value="N/A")

with col2:
    try:
        avg_earnings = get_latest_value('CES0500000003')
        if avg_earnings is not None:
            st.metric(
                label="Avg Hourly Earnings",
                value=f"${avg_earnings:.2f}",
                help="Average hourly earnings, all employees"
            )
        else:
            st.metric(label="Avg Hourly Earnings", value="N/A")
    except:
        st.metric(label="Avg Hourly Earnings", value="N/A")

with col3:
    try:
        civpart = get_latest_value('CIVPART')
        if civpart is not None:
            st.metric(
                label="Labor Force Participation",
                value=f"{civpart:.1f}%",
                help="Percentage of population in labor force"
            )
        else:
            st.metric(label="Labor Force Participation", value="N/A")
    except:
        st.metric(label="Labor Force Participation", value="N/A")

with col4:
    try:
        icsa = get_latest_value('ICSA')
        if icsa is not None:
            st.metric(
                label="Initial Jobless Claims",
                value=f"{icsa:.0f}K",
                help="Weekly initial unemployment claims"
            )
        else:
            st.metric(label="Initial Jobless Claims", value="N/A")
    except:
        st.metric(label="Initial Jobless Claims", value="N/A")

st.divider()

# ========== CONSUMER & HOUSING ==========
st.markdown('<div class="section-header"><h3>🏠 Consumer & Housing</h3></div>', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)

with col1:
    try:
        pce = get_latest_value('PCE')
        if pce is not None:
            st.metric(
                label="Personal Consumption",
                value=f"${pce/1000:.1f}T",
                help="Personal consumption expenditures in billions"
            )
        else:
            st.metric(label="Personal Consumption", value="N/A")
    except:
        st.metric(label="Personal Consumption", value="N/A")

with col2:
    try:
        psavert = get_latest_value('PSAVERT')
        if psavert is not None:
            st.metric(
                label="Personal Saving Rate",
                value=f"{psavert:.1f}%",
                help="Personal savings as % of disposable income"
            )
        else:
            st.metric(label="Personal Saving Rate", value="N/A")
    except:
        st.metric(label="Personal Saving Rate", value="N/A")

with col3:
    try:
        houst = get_latest_value('HOUST')
        if houst is not None:
            st.metric(
                label="Housing Starts",
                value=f"{houst:.0f}K",
                help="New housing units started (thousands)"
            )
        else:
            st.metric(label="Housing Starts", value="N/A")
    except:
        st.metric(label="Housing Starts", value="N/A")

with col4:
    try:
        mortgage = get_latest_value('MORTGAGE30US')
        if mortgage is not None:
            st.metric(
                label="30-Year Mortgage Rate",
                value=f"{mortgage:.2f}%",
                help="Average 30-year fixed mortgage rate"
            )
        else:
            st.metric(label="30-Year Mortgage Rate", value="N/A")
    except:
        st.metric(label="30-Year Mortgage Rate", value="N/A")

st.divider()

# ========== CHARTS SECTION ==========
st.markdown('<div class="section-header"><h3>📈 Economic Trends</h3></div>', unsafe_allow_html=True)

col_left, col_right = st.columns(2)

# Left Column: GDP Growth Trend
with col_left:
    st.markdown("#### Real GDP Growth (Last 5 Years)")
    try:
        gdp_data = load_fred_data({'Real GDP Growth': 'A191RL1Q225SBEA'})
        if not gdp_data.empty:
            # Filter last 5 years
            five_years_ago = datetime.now() - timedelta(days=365*5)
            gdp_recent = gdp_data[gdp_data.index >= five_years_ago]
            
            fig_gdp = px.line(
                gdp_recent,
                x=gdp_recent.index,
                y='Real GDP Growth',
                labels={'Real GDP Growth': 'Growth Rate (%)', 'index': 'Date'}
            )
            
            fig_gdp.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            fig_gdp.update_layout(
                height=350,
                margin=dict(l=0, r=0, t=0, b=0),
                hovermode='x unified',
                showlegend=False
            )
            fig_gdp.update_traces(line_color='#0068c9', line_width=2)
            
            st.plotly_chart(fig_gdp, use_container_width=True)
        else:
            st.info("GDP growth data not available")
    except Exception as e:
        st.error(f"Error loading GDP chart: {str(e)}")

# Right Column: Unemployment Rate Trend
with col_right:
    st.markdown("#### Unemployment Rate (Last 5 Years)")
    try:
        unemp_data = load_fred_data({'Unemployment Rate': 'UNRATE'})
        if not unemp_data.empty:
            # Filter last 5 years
            five_years_ago = datetime.now() - timedelta(days=365*5)
            unemp_recent = unemp_data[unemp_data.index >= five_years_ago]
            
            fig_unemp = px.line(
                unemp_recent,
                x=unemp_recent.index,
                y='Unemployment Rate',
                labels={'Unemployment Rate': 'Unemployment Rate (%)', 'index': 'Date'}
            )
            
            fig_unemp.update_layout(
                height=350,
                margin=dict(l=0, r=0, t=0, b=0),
                hovermode='x unified',
                showlegend=False
            )
            fig_unemp.update_traces(line_color='#ff6b6b', line_width=2)
            
            st.plotly_chart(fig_unemp, use_container_width=True)
        else:
            st.info("Unemployment data not available")
    except Exception as e:
        st.error(f"Error loading unemployment chart: {str(e)}")

# Footer with navigation
st.divider()

# Navigation Section
st.markdown('<div class="section-header"><h3>🧭 Explore Analytics</h3></div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="nav-card">
        <h4>📊 GDP & Growth</h4>
        <p>Deep dive into economic growth, GDP components, and productivity metrics</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="nav-card" style="margin-top: 1rem;">
        <h4>💹 Inflation & Prices</h4>
        <p>Track consumer prices, producer prices, and inflation expectations</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="nav-card">
        <h4>💼 Employment</h4>
        <p>Labor market trends, wages, and workforce participation analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="nav-card" style="margin-top: 1rem;">
        <h4>🏠 Consumer & Housing</h4>
        <p>Spending patterns, savings, retail sales, and housing market data</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="nav-card">
        <h4>📈 Market Indices</h4>
        <p>Global market performance, sector heatmaps, and correlation analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="nav-card" style="margin-top: 1rem;">
        <h4>🔑 API Management</h4>
        <p>Configure FRED API key for authenticated access and higher limits</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("")
st.info("💡 **Tip:** Start in Macro Core tabs, then use the readiness matrix to know which pages are API-blocked.")

render_navigation_hub()
st.divider()
render_data_readiness_matrix()

# Professional Footer
st.markdown("""
<div class="footer">
    <p>Built with ❤️ by <strong>Moshe Sham</strong></p>
    <p style="font-size: 0.75rem; margin-top: 0.5rem;">
        Powered by FRED API • Yahoo Finance • Streamlit • Plotly
    </p>
</div>
""", unsafe_allow_html=True)

# Sidebar information
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0;">
        <h2 style="margin: 0; color: #0068c9;">📊 Economic Dashboard</h2>
        <p style="color: rgba(255,255,255,0.6); font-size: 0.85rem; margin-top: 0.5rem;">Professional Analytics Platform</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    st.markdown("### 📋 Quick Overview")
    st.markdown("""
    Monitor **60+ economic indicators** including:
    
    - 📊 **GDP & Growth** — Real GDP, productivity
    - 💰 **Inflation** — CPI, PCE, expectations
    - 💼 **Employment** — Jobs, wages, claims
    - 🏠 **Housing** — Starts, mortgage rates
    - 📈 **Markets** — Indices, yields, volatility
    """)

    st.markdown("### 🚀 Quick Launch")
    with st.expander("Macro Core", expanded=True):
        for page in DASHBOARD_CATALOG:
            if page["group"] == "Macro Core":
                st.page_link(page["path"], label=page["name"], icon="📍")

    with st.expander("Research and ML"):
        for page in DASHBOARD_CATALOG:
            if page["group"] == "Research and ML":
                st.page_link(page["path"], label=page["name"], icon="🧠")

    with st.expander("API-dependent pages"):
        for page in DASHBOARD_CATALOG:
            if page["status"] == "API Required":
                st.page_link(page["path"], label=page["name"], icon="🔒")

    st.divider()
    
    # Connection Status
    st.markdown("### 🔌 Connection Status")
    if is_offline_mode():
        st.warning("**Offline Mode**\n\nUsing cached/sample data")
    else:
        st.success("**Online**\n\nConnected to live data feeds")
    
    # API Key status
    st.divider()
    st.markdown("### 🔑 API Status")
    creds_manager = get_credentials_manager()
    if creds_manager.has_api_key('fred'):
        st.success("✅ FRED API Authenticated")
    else:
        st.warning("⚠️ Using free tier")
        st.caption("Configure API key for higher limits")

    # Show data availability
    with st.expander("📊 Data Availability"):
        fred_status = "✅ Available" if can_use_offline_data('fred') else "❌ Not available"
        st.markdown(f"**FRED Data:** {fred_status}")
        
        st.markdown("**Series Tracked:**")
        metrics_data = {
            "GDP & Growth": 4,
            "Inflation": 5,
            "Employment": 6,
            "Consumer": 6,
            "Housing": 4,
            "Interest Rates": 5
        }
        for category, count in metrics_data.items():
            st.markdown(f"• {category}: {count} series")

    with st.expander("⏱️ Data Freshness Monitor"):
        try:
            fetcher = get_incremental_fetcher()
            watermarks = fetcher.get_all_watermarks()
            if watermarks.empty:
                st.caption("No watermark records yet. Run scheduled refresh jobs first.")
            else:
                watermarks['last_fetched_date'] = pd.to_datetime(watermarks['last_fetched_date'], errors='coerce')
                latest_per_source = watermarks.sort_values('last_fetched_date').groupby('source').tail(1)
                for _, row in latest_per_source.sort_values('source').iterrows():
                    source = str(row['source'])
                    status = str(row.get('status', 'unknown')).lower()
                    latest_date = row.get('last_fetched_date')
                    date_txt = latest_date.strftime('%Y-%m-%d') if pd.notna(latest_date) else 'N/A'
                    records = int(row.get('records_fetched', 0) or 0)

                    if status == 'ok':
                        st.success(f"{source}: {date_txt} ({records} new)")
                    elif status == 'error':
                        st.error(f"{source}: last run failed")
                    else:
                        st.warning(f"{source}: status {status}")

                stale = fetcher.get_stale_series(max_age_days=2)
                if not stale.empty:
                    st.warning(f"{len(stale)} series are older than 2 days")
        except Exception as e:
            st.caption(f"Freshness monitor unavailable: {e}")

    st.divider()
    
    # Footer
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0; color: rgba(255,255,255,0.5); font-size: 0.75rem;">
        <p>v1.0.0</p>
        <p>Built with Streamlit</p>
    </div>
    """, unsafe_allow_html=True)
