"""
Census EITS Explorer
Browse and chart Census EITS indicators loaded into PostgreSQL.
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from modules.database.factory import get_db_connection


st.set_page_config(page_title='Census EITS Explorer', page_icon='🏛️', layout='wide')
st.title('🏛️ Census EITS Explorer')
st.caption('US Census Economic Indicator Time Series loaded from PostgreSQL')


def load_available_indicators() -> pd.DataFrame:
    db = get_db_connection()
    query = (
        'SELECT indicator, COUNT(*) AS row_count, MIN(date) AS min_date, MAX(date) AS max_date '
        'FROM census_data GROUP BY indicator ORDER BY indicator'
    )
    return db.query(query)


def load_indicator_data(indicator: str, start_date: str, end_date: str, limit: int) -> pd.DataFrame:
    db = get_db_connection()
    query = (
        'SELECT date, indicator, category, value, seasonally_adjusted '
        'FROM census_data '
        'WHERE indicator = ? AND date >= ? AND date <= ? '
        'ORDER BY date, category '
        f'LIMIT {int(limit)}'
    )
    return db.query(query, (indicator, start_date, end_date))


catalog = load_available_indicators()
if catalog.empty:
    st.warning('No Census data found in PostgreSQL yet.')
    st.stop()

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    indicator = st.selectbox('Indicator', catalog['indicator'].tolist(), index=0)
with col2:
    start_date = st.date_input('Start Date', value=pd.to_datetime(catalog['min_date'].min()).date())
with col3:
    end_date = st.date_input('End Date', value=pd.to_datetime(catalog['max_date'].max()).date())

limit = st.slider('Max rows to fetch', min_value=500, max_value=100000, value=20000, step=500)

selected_meta = catalog[catalog['indicator'] == indicator].iloc[0]
st.markdown(
    f"Rows: {int(selected_meta['row_count']):,} | Range: {selected_meta['min_date']} to {selected_meta['max_date']}"
)

with st.spinner('Loading Census series...'):
    df = load_indicator_data(indicator, str(start_date), str(end_date), limit)

if df.empty:
    st.info('No rows for selected filters.')
    st.stop()

# Plot top categories by density to keep the chart readable.
cat_counts = df.groupby('category', dropna=False).size().sort_values(ascending=False)
max_categories = st.slider('Max categories in chart', min_value=1, max_value=20, value=8)
selected_categories = cat_counts.head(max_categories).index.tolist()
plot_df = df[df['category'].isin(selected_categories)].copy()
plot_df['date'] = pd.to_datetime(plot_df['date'])

fig = px.line(
    plot_df,
    x='date',
    y='value',
    color='category',
    title=f'{indicator} (Top {len(selected_categories)} categories)'
)
fig.update_layout(height=500)
st.plotly_chart(fig, use_container_width=True)

st.subheader('Raw Data Preview')
st.dataframe(df.head(1000), use_container_width=True)
