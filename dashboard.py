import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from fredapi import Fred
import time

# --- CONFIG ---
fred = Fred(api_key=st.secrets["FRED_API_KEY"])

# --- PASSWORD PROTECTION ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.markdown("""
            <style>
            .block-container {max-width: 400px; margin: auto; padding-top: 15%;}
            .stTextInput input {background-color: #1a1a1a; color: #ff8c00; border: 1px solid #ff8c00;}
            .stButton button {background-color: #ff8c00; color: black; font-weight: bold; width: 100%;}
            </style>
        """, unsafe_allow_html=True)
        st.markdown("## 🖥️ MACRO TERMINAL")
        st.markdown("#### Restricted Access")
        password = st.text_input("Password", type="password")
        if st.button("LOGIN"):
            if password == st.secrets["DASHBOARD_PASSWORD"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Wrong password")
        return False
    return True

if not check_password():
    st.stop()

# --- PAGE SETUP ---
st.set_page_config(page_title="Macro Terminal", layout="wide")

st.markdown("""
    <style>
    body, .stApp { background-color: #0a0a0a; }
    .block-container { padding: 1rem 2rem; }
    h1, h2, h3 { color: #ff8c00 !important; font-family: monospace; }
    .stMetric { background-color: #111111; border: 1px solid #ff8c00; padding: 10px; border-radius: 4px; }
    .stMetric label { color: #ff8c00 !important; font-family: monospace; font-size: 0.75rem; }
    .stMetric [data-testid="stMetricValue"] { color: white !important; font-family: monospace; }
    .stMetric [data-testid="stMetricDelta"] { font-family: monospace; }
    div[data-testid="stHorizontalBlock"] { gap: 0.5rem; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align:center; letter-spacing: 8px;'>⬛ MACRO TERMINAL</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#666; font-family:monospace;'>FRED · ST. LOUIS FED · LIVE DATA</p>", unsafe_allow_html=True)
st.divider()

# --- FETCH DATA ---
@st.cache_data(ttl=86400)
def load_data():
    cpi = fred.get_series('CPIAUCSL', observation_start='2015-01-01')
    y2 = fred.get_series('DGS2', observation_start='2015-01-01')
    y10 = fred.get_series('DGS10', observation_start='2015-01-01')
    breakeven = fred.get_series('T10YIE', observation_start='2015-01-01')
    fed_funds = fred.get_series('FEDFUNDS', observation_start='2015-01-01')
    return cpi, y2, y10, breakeven, fed_funds

cpi, y2, y10, breakeven, fed_funds = load_data()
cpi_yoy = cpi.pct_change(12) * 100

# --- CHART STYLE ---
BLOOMBERG_LAYOUT = dict(
    paper_bgcolor='#0a0a0a',
    plot_bgcolor='#0f0f0f',
    font=dict(color='#ff8c00', family='monospace', size=11),
    xaxis=dict(gridcolor='#1a1a1a', showgrid=True, zeroline=False),
    yaxis=dict(gridcolor='#1a1a1a', showgrid=True, zeroline=False),
    margin=dict(l=40, r=20, t=30, b=40),
    height=280,
)

def make_line_chart(df, x, y, color='#ff8c00', title=''):
    fig = go.Figure()
    if isinstance(y, list):
        colors = ['#ff8c00', '#00bfff']
        for i, col in enumerate(y):
            fig.add_trace(go.Scatter(x=df[x], y=df[col], name=col,
                         line=dict(color=colors[i], width=1.5)))
    else:
        fig.add_trace(go.Scatter(x=df[x], y=df[y], name=y,
                     line=dict(color=color, width=1.5), fill='tozeroy',
                     fillcolor='rgba(255,140,0,0.05)'))
    layout = BLOOMBERG_LAYOUT.copy()
    layout['title'] = dict(text=title, font=dict(color='#ff8c00', size=12))
    fig.update_layout(**layout)
    return fig

# --- REGIME METRICS ---
latest_cpi = round(cpi_yoy.dropna().iloc[-1], 2)
latest_spread = round((y10 - y2).dropna().iloc[-1], 2)
latest_breakeven = round(breakeven.dropna().iloc[-1], 2)
latest_fed = round(fed_funds.dropna().iloc[-1], 2)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("CPI INFLATION (YoY)", f"{latest_cpi}%", "HIGH" if latest_cpi > 3 else "NORMAL")
with col2:
    st.metric("YIELD CURVE SPREAD", f"{latest_spread}%", "⚠️ INVERTED" if latest_spread < 0 else "NORMAL")
with col3:
    st.metric("10Y BREAKEVEN", f"{latest_breakeven}%", "ABOVE TARGET" if latest_breakeven > 2 else "BELOW TARGET")
with col4:
    st.metric("FED FUNDS RATE", f"{latest_fed}%", "RESTRICTIVE" if latest_fed > 4 else "NEUTRAL")

st.divider()

# --- ROW 1: CPI + YIELDS ---
col_left, col_right = st.columns(2)

with col_left:
    cpi_df = cpi_yoy.dropna().reset_index()
    cpi_df.columns = ['Date', 'CPI YoY %']
    fig = make_line_chart(cpi_df, 'Date', 'CPI YoY %', title='CPI INFLATION YoY %')
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    yields_df = pd.DataFrame({'2Y': y2, '10Y': y10}).dropna().reset_index()
    yields_df.columns = ['Date', '2Y', '10Y']
    fig = make_line_chart(yields_df, 'Date', ['2Y', '10Y'], title='TREASURY YIELDS 2Y vs 10Y')
    st.plotly_chart(fig, use_container_width=True)

# --- ROW 2: SPREAD + BREAKEVEN + FED FUNDS ---
col1, col2, col3 = st.columns(3)

with col1:
    yields_df['Spread'] = yields_df['10Y'] - yields_df['2Y']
    fig = make_line_chart(yields_df, 'Date', 'Spread', title='YIELD CURVE SPREAD (10Y-2Y)')
    fig.add_hline(y=0, line_dash="dash", line_color="#ff3333", line_width=1)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    be_df = breakeven.dropna().reset_index()
    be_df.columns = ['Date', 'Breakeven %']
    fig = make_line_chart(be_df, 'Date', 'Breakeven %', title='10Y INFLATION BREAKEVEN')
    fig.add_hline(y=2, line_dash="dash", line_color="#00ff88", line_width=1)
    st.plotly_chart(fig, use_container_width=True)

with col3:
    ff_df = fed_funds.dropna().reset_index()
    ff_df.columns = ['Date', 'Fed Funds %']
    fig = make_line_chart(ff_df, 'Date', 'Fed Funds %', title='FED FUNDS RATE')
    st.plotly_chart(fig, use_container_width=True)