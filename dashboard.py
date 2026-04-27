import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from fredapi import Fred
import yfinance as yf

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
        st.markdown("## TRADING TERMINAL")
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
st.set_page_config(page_title="Trading Terminal", layout="wide")
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
    .stTabs [data-baseweb="tab-list"] { gap: 4px; background-color: #0a0a0a; }
    .stTabs [data-baseweb="tab"] { background-color: #111111; border: 1px solid #333; color: #888; font-family: monospace; font-size: 0.8rem; letter-spacing: 2px; padding: 8px 20px; }
    .stTabs [aria-selected="true"] { background-color: #1a1a1a !important; border-color: #ff8c00 !important; color: #ff8c00 !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align:center; letter-spacing: 8px;'> TRADING TERMINAL</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#666; font-family:monospace;'>FRED · ST. LOUIS FED · YAHOO FINANCE · LIVE DATA</p>", unsafe_allow_html=True)
st.divider()

# --- CHART HELPERS ---
def base_layout(accent='#ff8c00'):
    return dict(
        paper_bgcolor='#0a0a0a',
        plot_bgcolor='#0f0f0f',
        font=dict(color=accent, family='monospace', size=11),
        xaxis=dict(gridcolor='#1a1a1a', showgrid=True, zeroline=False),
        yaxis=dict(gridcolor='#1a1a1a', showgrid=True, zeroline=False),
        margin=dict(l=40, r=20, t=35, b=40),
        height=280,
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=10)),
    )

def make_chart(df, x, y, color='#ff8c00', title='', accent='#ff8c00'):
    layout = base_layout(accent)
    layout['title'] = dict(text=title, font=dict(color=accent, size=12))
    fig = go.Figure()
    if isinstance(y, list):
        colors = [color, '#00bfff']
        for i, col in enumerate(y):
            fig.add_trace(go.Scatter(x=df[x], y=df[col], name=col,
                line=dict(color=colors[i], width=1.5)))
    else:
        fill_rgba = 'rgba(255,215,0,0.05)' if accent == '#ff8c00' else 'rgba(255,140,0,0.05)'
        fig.add_trace(go.Scatter(x=df[x], y=df[y], name=y,
            line=dict(color=color, width=1.5),
            fill='tozeroy', fillcolor=fill_rgba))
    fig.update_layout(**layout)
    return fig

# ==============================================================
# DATA LOADERS
# ==============================================================

@st.cache_data(ttl=86400)
def load_macro_data():
    cpi       = fred.get_series('CPIAUCSL',  observation_start='2015-01-01')
    y2        = fred.get_series('DGS2',      observation_start='2015-01-01')
    y10       = fred.get_series('DGS10',     observation_start='2015-01-01')
    breakeven = fred.get_series('T10YIE',    observation_start='2015-01-01')
    fed_funds = fred.get_series('FEDFUNDS',  observation_start='2015-01-01')
    return cpi, y2, y10, breakeven, fed_funds

@st.cache_data(ttl=3600)
def load_gold_data():
    # Gold & Silver from Yahoo Finance — no API restrictions
    gold_raw   = yf.download('GC=F', start='2015-01-01', auto_adjust=True, progress=False)
silver_raw = yf.download('SI=F', start='2015-01-01', auto_adjust=True, progress=False)

# Fallback to ETFs if futures return empty
if gold_raw.empty:
    gold_raw = yf.download('GLD', start='2015-01-01', auto_adjust=True, progress=False)
if silver_raw.empty:
    silver_raw = yf.download('SLV', start='2015-01-01', auto_adjust=True, progress=False)

gold   = gold_raw['Close'].squeeze().dropna()
silver = silver_raw['Close'].squeeze().dropna()

    # FRED series — all freely redistributable
tips      = fred.get_series('DFII10',     observation_start='2015-01-01')
    breakeven = fred.get_series('T10YIE',     observation_start='2015-01-01')
    dxy       = fred.get_series('DTWEXBGS',   observation_start='2015-01-01')
    fed_funds = fred.get_series('FEDFUNDS',   observation_start='2015-01-01')
    oil       = fred.get_series('DCOILWTICO', observation_start='2015-01-01')

    return gold, silver, tips, breakeven, dxy, fed_funds, oil

# ==============================================================
# TABS
# ==============================================================
tab1, tab2 = st.tabs(["MACRO", "XAUUSD"])

# ==============================================================
# TAB 1 — MACRO
# ==============================================================
with tab1:
    cpi, y2, y10, breakeven, fed_funds = load_macro_data()
    cpi_yoy = cpi.pct_change(12) * 100

    latest_cpi       = round(cpi_yoy.dropna().iloc[-1], 2)
    latest_spread    = round((y10 - y2).dropna().iloc[-1], 2)
    latest_breakeven = round(breakeven.dropna().iloc[-1], 2)
    latest_fed       = round(fed_funds.dropna().iloc[-1], 2)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("CPI INFLATION (YoY)", f"{latest_cpi}%",
                  "HIGH" if latest_cpi > 3 else "NORMAL")
    with col2:
        st.metric("YIELD CURVE SPREAD", f"{latest_spread}%",
                  "⚠️ INVERTED" if latest_spread < 0 else "NORMAL")
    with col3:
        st.metric("10Y BREAKEVEN", f"{latest_breakeven}%",
                  "ABOVE TARGET" if latest_breakeven > 2 else "BELOW TARGET")
    with col4:
        st.metric("FED FUNDS RATE", f"{latest_fed}%",
                  "RESTRICTIVE" if latest_fed > 4 else "NEUTRAL")

    st.divider()

    col_left, col_right = st.columns(2)
    with col_left:
        cpi_df = cpi_yoy.dropna().reset_index()
        cpi_df.columns = ['Date', 'CPI YoY %']
        fig = make_chart(cpi_df, 'Date', 'CPI YoY %', title='CPI INFLATION YoY %')
        st.plotly_chart(fig, use_container_width=True)
    with col_right:
        yields_df = pd.DataFrame({'2Y': y2, '10Y': y10}).dropna().reset_index()
        yields_df.columns = ['Date', '2Y', '10Y']
        fig = make_chart(yields_df, 'Date', ['2Y', '10Y'], title='TREASURY YIELDS 2Y vs 10Y')
        st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        yields_df['Spread'] = yields_df['10Y'] - yields_df['2Y']
        fig = make_chart(yields_df, 'Date', 'Spread', title='YIELD CURVE SPREAD (10Y-2Y)')
        fig.add_hline(y=0, line_dash="dash", line_color="#ff3333", line_width=1)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        be_df = breakeven.dropna().reset_index()
        be_df.columns = ['Date', 'Breakeven %']
        fig = make_chart(be_df, 'Date', 'Breakeven %', title='10Y INFLATION BREAKEVEN')
        fig.add_hline(y=2, line_dash="dash", line_color="#00ff88", line_width=1)
        st.plotly_chart(fig, use_container_width=True)
    with col3:
        ff_df = fed_funds.dropna().reset_index()
        ff_df.columns = ['Date', 'Fed Funds %']
        fig = make_chart(ff_df, 'Date', 'Fed Funds %', title='FED FUNDS RATE')
        st.plotly_chart(fig, use_container_width=True)

# ==============================================================
# TAB 2 — GOLD
# ==============================================================
with tab2:
    st.markdown("""
        <style>
        [data-testid="stMetric"] { border-color: #ff8c00 !important; }
        [data-testid="stMetric"] label { color: #ff8c00 !important; }
        </style>
    """, unsafe_allow_html=True)

    gold, silver, tips, breakeven_g, dxy, fed_funds_g, oil = load_gold_data()

    # Derived
    gold_silver_ratio = (gold / silver).dropna()
    tips_clean = tips.dropna()
    dxy_clean  = dxy.dropna()
    be_clean   = breakeven_g.dropna()

    # Latest values
    latest_gold  = round(float(gold.dropna().iloc[-1]), 2)
    gold_1m      = round(float(gold.dropna().iloc[-22]), 2) if len(gold.dropna()) > 22 else latest_gold
    gold_chg_pct = round(((latest_gold - gold_1m) / gold_1m) * 100, 2)
    latest_tips  = round(float(tips_clean.iloc[-1]), 2)
    latest_dxy   = round(float(dxy_clean.iloc[-1]), 2)
    latest_gsr   = round(float(gold_silver_ratio.iloc[-1]), 1)
    latest_be    = round(float(be_clean.iloc[-1]), 2)
    latest_fed_g = round(float(fed_funds_g.dropna().iloc[-1]), 2)

    # Signal logic
    tips_sig = "🟢 VERY BULLISH" if latest_tips < 0 else ("🟢 BULLISH" if latest_tips < 0.75 else ("🟡 NEUTRAL" if latest_tips < 1.5 else "🔴 BEARISH"))
    dxy_sig  = "🟢 DOLLAR WEAK" if latest_dxy < 98 else ("🟡 NEUTRAL" if latest_dxy < 103 else "🔴 DOLLAR STRONG")
    gsr_sig  = "🟡 FEAR BID" if latest_gsr > 90 else ("🟢 RISK ON" if latest_gsr < 70 else "🟡 NEUTRAL")
    be_sig   = "🟢 INFLATIONARY" if latest_be > 2.5 else ("🟡 ON TARGET" if latest_be > 2.0 else "🔴 BELOW TARGET")
    fed_sig  = "🔴 RESTRICTIVE" if latest_fed_g > 4 else "🟡 NEUTRAL"

    # Metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("XAUUSD (USD/oz)", f"${latest_gold:,.2f}",
                  f"{'+' if gold_chg_pct >= 0 else ''}{gold_chg_pct}% (1M)")
    with col2:
        st.metric("10Y TIPS REAL YIELD", f"{latest_tips}%", tips_sig)
    with col3:
        st.metric("DXY DOLLAR INDEX", f"{latest_dxy:.1f}", dxy_sig)
    with col4:
        st.metric("GOLD/SILVER RATIO", f"{latest_gsr}", gsr_sig)
    with col5:
        st.metric("10Y BREAKEVEN", f"{latest_be}%", be_sig)

    st.divider()

    # Row 1: Gold price + TIPS
    col_left, col_right = st.columns(2)
    with col_left:
        g_df = gold.dropna().reset_index()
        g_df.columns = ['Date', 'XAUUSD']
        fig = make_chart(g_df, 'Date', 'XAUUSD',
                         color='#ff8c00', title='XAUUSD SPOT PRICE (USD/oz)', accent='#ff8c00')
        st.plotly_chart(fig, use_container_width=True)
    with col_right:
        tips_df = tips_clean.reset_index()
        tips_df.columns = ['Date', 'TIPS Real Yield %']
        fig = make_chart(tips_df, 'Date', 'TIPS Real Yield %',
                         color='#ff8c00', title='10Y TIPS REAL YIELD % — Primary gold driver', accent='#ff8c00')
        fig.add_hline(y=0, line_dash="dash", line_color="#ff3333", line_width=1,
                      annotation_text="0% — breakout zone",
                      annotation_position="bottom right",
                      annotation_font=dict(color="#ff3333", size=10))
        st.plotly_chart(fig, use_container_width=True)

    # Row 2: DXY + Gold/Silver + Breakeven
    col1, col2, col3 = st.columns(3)
    with col1:
        dxy_df = dxy_clean.reset_index()
        dxy_df.columns = ['Date', 'DXY']
        fig = make_chart(dxy_df, 'Date', 'DXY',
                         color='#ff8c00', title='DXY DOLLAR INDEX — Inverse correlation', accent='#ff8c00')
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        gsr_df = gold_silver_ratio.reset_index()
        gsr_df.columns = ['Date', 'Gold/Silver Ratio']
        fig = make_chart(gsr_df, 'Date', 'Gold/Silver Ratio',
                         color='#ff8c00', title='GOLD / SILVER RATIO — Fear indicator', accent='#ff8c00')
        fig.add_hline(y=80, line_dash="dash", line_color="#00ff88", line_width=1,
                      annotation_text="80 — hist. avg",
                      annotation_position="top right",
                      annotation_font=dict(color="#00ff88", size=10))
        fig.add_hline(y=90, line_dash="dash", line_color="#ff3333", line_width=1,
                      annotation_text="90 — extreme",
                      annotation_position="bottom right",
                      annotation_font=dict(color="#ff3333", size=10))
        st.plotly_chart(fig, use_container_width=True)
    with col3:
        be_df = be_clean.reset_index()
        be_df.columns = ['Date', 'Breakeven %']
        fig = make_chart(be_df, 'Date', 'Breakeven %',
                         color='#ff8c00', title='10Y BREAKEVEN INFLATION', accent='#ff8c00')
        fig.add_hline(y=2, line_dash="dash", line_color="#00ff88", line_width=1,
                      annotation_text="2% Fed target",
                      annotation_position="bottom right",
                      annotation_font=dict(color="#00ff88", size=10))
        st.plotly_chart(fig, use_container_width=True)

    # Row 3: Gold vs TIPS dual axis + Oil
    col_left, col_right = st.columns(2)
    with col_left:
        combined = pd.DataFrame({'Gold': gold, 'TIPS': tips}).dropna().reset_index()
        combined.columns = ['Date', 'Gold', 'TIPS']
        layout = base_layout('#ff8c00')
        layout['title']  = dict(text='XAUUSD vs 10Y TIPS (inverted RHS)',
                                font=dict(color='#ff8c00', size=12))
        layout['yaxis']  = dict(gridcolor='#1a1a1a', showgrid=True, zeroline=False,
                                title='Gold (USD/oz)', color='#ff8c00')
        layout['yaxis2'] = dict(overlaying='y', side='right', autorange='reversed',
                                showgrid=False, zeroline=False,
                                title='TIPS % (inv.)', color='#00bfff')
        layout['legend'] = dict(orientation='h', y=-0.2, font=dict(size=10))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=combined['Date'], y=combined['Gold'],
            name='XAUUSD', line=dict(color='#ff8c00', width=1.5)))
        fig.add_trace(go.Scatter(x=combined['Date'], y=combined['TIPS'],
            name='TIPS (inv.)', line=dict(color='#00bfff', width=1.5, dash='dot'),
            yaxis='y2'))
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True)
    with col_right:
        oil_df = oil.dropna().reset_index()
        oil_df.columns = ['Date', 'WTI (USD/bbl)']
        fig = make_chart(oil_df, 'Date', 'WTI (USD/bbl)',
                         color='#ff8c00', title='WTI CRUDE OIL — Inflation proxy', accent='#ff8c00')
        st.plotly_chart(fig, use_container_width=True)

    # Signal summary
    st.divider()
    st.markdown("<p style='font-family:monospace; color:#ff8c00; font-size:0.75rem; letter-spacing:4px;'>MACRO SIGNAL SUMMARY · XAUUSD</p>", unsafe_allow_html=True)

    signals = [
        ("10Y TIPS REAL YIELD",     f"{latest_tips}%",    tips_sig,
         "Primary driver. Below 0% = structural gold bid. Above 1.5% = headwind. Watch this first."),
        ("DXY DOLLAR INDEX",        f"{latest_dxy:.1f}",  dxy_sig,
         "~-0.85 correlation with gold on a 30-day basis. Dollar weakness = gold tailwind."),
        ("GOLD / SILVER RATIO",     f"{latest_gsr}",      gsr_sig,
         "Above 90 = fear/safe-haven bid, risk of mean reversion. Below 70 = risk appetite, momentum."),
        ("10Y BREAKEVEN INFLATION", f"{latest_be}%",      be_sig,
         "Rising breakevens compress real yields. Above 2.5% = inflationary backdrop, gold supportive."),
        ("FED FUNDS RATE",          f"{latest_fed_g}%",   fed_sig,
         "Rate cuts = falling real yields = gold bullish. Watch TIPS more than the Fed funds rate itself."),
    ]

    color_map = {"🟢": "#00ff88", "🔴": "#ff3333", "🟡": "#ff8c00"}

    for name, value, sig, desc in signals:
        dot_color = color_map.get(sig[0], "#888888")
        st.markdown(f"""
            <div style="display:flex; align-items:flex-start; gap:12px; padding:10px 0;
                        border-bottom: 0.5px solid #1a1a1a;">
                <div style="width:8px; height:8px; border-radius:50%; background:{dot_color};
                            margin-top:5px; flex-shrink:0;"></div>
                <div style="flex:1;">
                    <span style="font-family:monospace; font-size:0.75rem; color:#ff8c00;">{name}</span>
                    <span style="font-family:monospace; font-size:0.75rem; color:#888; margin-left:8px;">{value}</span>
                    <span style="font-family:monospace; font-size:0.75rem; color:{dot_color}; margin-left:8px;">· {sig[1:]}</span>
                    <p style="font-family:monospace; font-size:0.7rem; color:#555; margin:3px 0 0;">{desc}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
