import streamlit as st
import pandas as pd
import plotly.express as px
from fredapi import Fred
import time

# --- CONFIG ---
FRED_API_KEY = "4f006a10edd2ccf6efd09fe95e7e8a8a"
fred = Fred(api_key=FRED_API_KEY)

# --- AUTO REFRESH every 24 hours ---
st.cache_data.clear() if 'last_refresh' not in st.session_state else None
st.session_state['last_refresh'] = time.time()

# --- PAGE SETUP ---
st.set_page_config(page_title="Macro Dashboard", layout="wide")
st.title("📊 Macro Dashboard")
st.caption("Data sourced from FRED · St. Louis Fed")

# --- FETCH DATA (cached for 24 hours) ---
@st.cache_data(ttl=86400)
def load_data():
    cpi = fred.get_series('CPIAUCSL', observation_start='2015-01-01')
    y2 = fred.get_series('DGS2', observation_start='2015-01-01')
    y10 = fred.get_series('DGS10', observation_start='2015-01-01')
    breakeven = fred.get_series('T10YIE', observation_start='2015-01-01')
    fed_funds = fred.get_series('FEDFUNDS', observation_start='2015-01-01')
    return cpi, y2, y10, breakeven, fed_funds

cpi, y2, y10, breakeven, fed_funds = load_data()

# --- CALCULATIONS ---
cpi_yoy = cpi.pct_change(12) * 100

# --- REGIME SUMMARY ---
latest_cpi = round(cpi_yoy.dropna().iloc[-1], 2)
latest_spread = round((y10 - y2).dropna().iloc[-1], 2)
latest_breakeven = round(breakeven.dropna().iloc[-1], 2)
latest_fed = round(fed_funds.dropna().iloc[-1], 2)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="CPI Inflation (YoY)", value=f"{latest_cpi}%",
              delta="High" if latest_cpi > 3 else "Normal")

with col2:
    st.metric(label="Yield Curve Spread", value=f"{latest_spread}%",
              delta="⚠️ Inverted" if latest_spread < 0 else "Normal")

with col3:
    st.metric(label="10Y Breakeven", value=f"{latest_breakeven}%",
              delta="Above target" if latest_breakeven > 2 else "Below target")

with col4:
    st.metric(label="Fed Funds Rate", value=f"{latest_fed}%",
              delta="Restrictive" if latest_fed > 4 else "Neutral")

# --- CPI CHART ---
cpi_df = cpi_yoy.dropna().reset_index()
cpi_df.columns = ['Date', 'CPI YoY %']
st.subheader("🔴 CPI Inflation (Year over Year %)")
fig_cpi = px.line(cpi_df, x='Date', y='CPI YoY %')
st.plotly_chart(fig_cpi, use_container_width=True)

# --- YIELDS CHART ---
yields_df = pd.DataFrame({'2Y': y2, '10Y': y10}).dropna().reset_index()
yields_df.columns = ['Date', '2Y', '10Y']
yields_df['Spread (10Y-2Y)'] = yields_df['10Y'] - yields_df['2Y']
st.subheader("📈 Treasury Yields (2Y vs 10Y)")
fig_yields = px.line(yields_df, x='Date', y=['2Y', '10Y'])
st.plotly_chart(fig_yields, use_container_width=True)

# --- YIELD CURVE SPREAD ---
st.subheader("⚠️ Yield Curve Spread (10Y - 2Y)")
fig_spread = px.line(yields_df, x='Date', y='Spread (10Y-2Y)')
fig_spread.add_hline(y=0, line_dash="dash", line_color="red")
st.plotly_chart(fig_spread, use_container_width=True)

# --- BREAKEVENS CHART ---
breakeven_df = breakeven.dropna().reset_index()
breakeven_df.columns = ['Date', 'Breakeven %']
st.subheader("💡 10Y Inflation Breakeven (Market Inflation Expectations)")
fig_breakeven = px.line(breakeven_df, x='Date', y='Breakeven %')
fig_breakeven.add_hline(y=2, line_dash="dash", line_color="green")
st.plotly_chart(fig_breakeven, use_container_width=True)

# --- FED FUNDS RATE ---
fed_funds_df = fed_funds.dropna().reset_index()
fed_funds_df.columns = ['Date', 'Fed Funds Rate %']
st.subheader("🏦 Fed Funds Rate")
fig_fed = px.line(fed_funds_df, x='Date', y='Fed Funds Rate %')
st.plotly_chart(fig_fed, use_container_width=True)
