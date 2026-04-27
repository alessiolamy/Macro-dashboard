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
    /* Gold accent for tab 2 metrics */
    .gold-metric .stMetric { border-color: #ffd700 !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align:center; letter-spacing: 8px;'>⬛ MACRO TERMINAL</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#666; font-family:monospace;'>FRED · ST. LOUIS FED · LIVE DATA</p>", unsafe_allow_html=True)
st.divider()

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

GOLD_LAYOUT = dict(
    paper_bgcolor='#0a0a0a',
    plot_bgcolor='#0f0f0f',
    font=dict(color='#ffd700', family='monospace', size=11),
    xaxis=dict(gridcolor='#1a1a1a', showgrid=True, zeroline=False),
    yaxis=dict(gridcolor='#1a1a1a', showgrid=True, zeroline=False),
    margin=dict(l=40, r=20, t=30, b=40),
    height=280,
)

def make_line_chart(df, x, y, color='#ff8c00', title='', gold=False):
    layout = GOLD_LAYOUT.copy() if gold else BLOOMBERG_LAYOUT.copy()
    fig = go.Figure()
    if isinstance(y, list):
        colors = ['#ffd700', '#00bfff'] if gold else ['#ff8c00', '#00bfff']
        for i, col in enumerate(y):
            fig.add_trace(go.Scatter(x=df[x], y=df[col], name=col,
                         line=dict(color=colors[i], width=1.5)))
    else:
        fill_color = 'rgba(255,215,0,0.05)' if gold else 'rgba(255,140,0,0.05)'
        fig.add_trace(go.Scatter(x=df[x], y=df[y], name=y,
                     line=dict(color=color, width=1.5), fill='tozeroy',
                     fillcolor=fill_color))
    layout['title'] = dict(text=title, font=dict(color='#ffd700' if gold else '#ff8c00', size=12))
    fig.update_layout(**layout)
    return fig

# --- FETCH MACRO DATA ---
@st.cache_data(ttl=86400)
def load_macro_data():
    cpi = fred.get_series('CPIAUCSL', observation_start='2015-01-01')
    y2 = fred.get_series('DGS2', observation_start='2015-01-01')
    y10 = fred.get_series('DGS10', observation_start='2015-01-01')
    breakeven = fred.get_series('T10YIE', observation_start='2015-01-01')
    fed_funds = fred.get_series('FEDFUNDS', observation_start='2015-01-01')
    return cpi, y2, y10, breakeven, fed_funds

# --- FETCH GOLD DATA ---
@st.cache_data(ttl=86400)
def load_gold_data():
    # XAUUSD spot price (London PM fix, USD per troy oz)
    gold = fred.get_series('GOLDAMGBD228NLBM', observation_start='2015-01-01')
    # 10Y TIPS real yield (key gold driver)
    tips = fred.get_series('DFII10', observation_start='2015-01-01')
    # 10Y breakeven inflation
    breakeven = fred.get_series('T10YIE', observation_start='2015-01-01')
    # DXY dollar index
    dxy = fred.get_series('DTWEXBGS', observation_start='2015-01-01')
    # Fed funds rate
    fed_funds = fred.get_series('FEDFUNDS', observation_start='2015-01-01')
    # Silver price (for Gold/Silver ratio)
    silver = fred.get_series('SLVPRUSD', observation_start='2015-01-01')
    # WTI crude oil
    oil = fred.get_series('DCOILWTICO', observation_start='2015-01-01')
    return gold, tips, breakeven, dxy, fed_funds, silver, oil

# --- TABS ---
tab1, tab2 = st.tabs(["📊  MACRO", "🥇  GOLD · XAUUSD"])

# ============================================================
# TAB 1 — MACRO
# ============================================================
with tab1:
    cpi, y2, y10, breakeven, fed_funds = load_macro_data()
    cpi_yoy = cpi.pct_change(12) * 100

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

# ============================================================
# TAB 2 — GOLD
# ============================================================
with tab2:
    st.markdown("""
        <style>
        /* Gold accent for metrics inside this tab */
        [data-testid="stMetric"] { border-color: #ffd700 !important; }
        [data-testid="stMetric"] label { color: #ffd700 !important; }
        </style>
    """, unsafe_allow_html=True)

    gold, tips, breakeven_g, dxy, fed_funds_g, silver, oil = load_gold_data()

    # Derived series
    gold_silver_ratio = (gold / silver).dropna()
    tips_clean = tips.dropna()
    dxy_clean = dxy.dropna()
    breakeven_g_clean = breakeven_g.dropna()
    fed_funds_g_clean = fed_funds_g.dropna()

    # Latest values
    latest_gold = round(gold.dropna().iloc[-1], 2)
    gold_1m_ago = round(gold.dropna().iloc[-22], 2) if len(gold.dropna()) > 22 else latest_gold
    gold_delta = round(latest_gold - gold_1m_ago, 2)
    gold_delta_pct = round((gold_delta / gold_1m_ago) * 100, 2)

    latest_tips = round(tips_clean.iloc[-1], 2)
    latest_dxy = round(dxy_clean.iloc[-1], 2)
    latest_gsr = round(gold_silver_ratio.iloc[-1], 1)
    latest_breakeven_g = round(breakeven_g_clean.iloc[-1], 2)

    # --- SIGNAL LOGIC ---
    tips_signal = "BULLISH" if latest_tips < 0.5 else ("BEARISH" if latest_tips > 1.5 else "NEUTRAL")
    dxy_signal = "BULLISH" if latest_dxy < 100 else ("BEARISH" if latest_dxy > 105 else "NEUTRAL")
    gsr_signal = "FEAR BID" if latest_gsr > 90 else ("BULLISH" if latest_gsr < 70 else "NEUTRAL")
    be_signal = "INFLATIONARY" if latest_breakeven_g > 2.5 else ("BELOW TARGET" if latest_breakeven_g < 2 else "ON TARGET")

    # --- METRIC ROW ---
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("XAUUSD SPOT (USD/oz)", f"${latest_gold:,.2f}",
                  f"{'+' if gold_delta >= 0 else ''}{gold_delta_pct}% (1M)")
    with col2:
        st.metric("10Y TIPS REAL YIELD", f"{latest_tips}%",
                  tips_signal)
    with col3:
        st.metric("DXY DOLLAR INDEX", f"{latest_dxy:.1f}",
                  dxy_signal)
    with col4:
        st.metric("GOLD / SILVER RATIO", f"{latest_gsr}",
                  gsr_signal)
    with col5:
        st.metric("10Y BREAKEVEN", f"{latest_breakeven_g}%",
                  be_signal)

    st.divider()

    # --- ROW 1: Gold price + TIPS real yield ---
    col_left, col_right = st.columns(2)
    with col_left:
        gold_df = gold.dropna().reset_index()
        gold_df.columns = ['Date', 'XAUUSD']
        fig = make_line_chart(gold_df, 'Date', 'XAUUSD', color='#ffd700',
                              title='XAUUSD SPOT PRICE (USD/oz)', gold=True)
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        tips_df = tips_clean.reset_index()
        tips_df.columns = ['Date', 'TIPS Real Yield %']
        fig = make_line_chart(tips_df, 'Date', 'TIPS Real Yield %', color='#ffd700',
                              title='10Y TIPS REAL YIELD % — Primary gold driver', gold=True)
        fig.add_hline(y=0, line_dash="dash", line_color="#ff3333", line_width=1,
                      annotation_text="0% — gold breakout zone", annotation_position="bottom right")
        st.plotly_chart(fig, use_container_width=True)

    # --- ROW 2: DXY + Gold/Silver ratio + Breakeven ---
    col1, col2, col3 = st.columns(3)
    with col1:
        dxy_df = dxy_clean.reset_index()
        dxy_df.columns = ['Date', 'DXY']
        fig = make_line_chart(dxy_df, 'Date', 'DXY', color='#ffd700',
                              title='DXY DOLLAR INDEX — Inverse correlation', gold=True)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        gsr_df = gold_silver_ratio.reset_index()
        gsr_df.columns = ['Date', 'Gold/Silver Ratio']
        fig = make_line_chart(gsr_df, 'Date', 'Gold/Silver Ratio', color='#ffd700',
                              title='GOLD / SILVER RATIO — Fear indicator', gold=True)
        fig.add_hline(y=80, line_dash="dash", line_color="#00ff88", line_width=1,
                      annotation_text="80 — hist. avg", annotation_position="top right")
        fig.add_hline(y=90, line_dash="dash", line_color="#ff3333", line_width=1,
                      annotation_text="90 — extreme fear", annotation_position="bottom right")
        st.plotly_chart(fig, use_container_width=True)

    with col3:
        be_df_g = breakeven_g_clean.reset_index()
        be_df_g.columns = ['Date', 'Breakeven %']
        fig = make_line_chart(be_df_g, 'Date', 'Breakeven %', color='#ffd700',
                              title='10Y BREAKEVEN INFLATION — Real yield context', gold=True)
        fig.add_hline(y=2, line_dash="dash", line_color="#00ff88", line_width=1,
                      annotation_text="2% Fed target", annotation_position="bottom right")
        st.plotly_chart(fig, use_container_width=True)

    # --- ROW 3: Gold vs TIPS overlay + Oil ---
    col_left, col_right = st.columns(2)
    with col_left:
        # Dual-axis: Gold price vs TIPS (inverted) — the key relationship
        combined = pd.DataFrame({
            'Gold': gold,
            'TIPS': tips
        }).dropna().reset_index()
        combined.columns = ['Date', 'Gold', 'TIPS']

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=combined['Date'], y=combined['Gold'],
            name='XAUUSD', line=dict(color='#ffd700', width=1.5),
            yaxis='y1'
        ))
        fig.add_trace(go.Scatter(
            x=combined['Date'], y=combined['TIPS'],
            name='TIPS Real Yield (inverted, RHS)',
            line=dict(color='#00bfff', width=1.5, dash='dot'),
            yaxis='y2'
        ))
        layout = GOLD_LAYOUT.copy()
        layout['title'] = dict(text='XAUUSD vs 10Y TIPS REAL YIELD (inverted)', font=dict(color='#ffd700', size=12))
        layout['yaxis'] = dict(gridcolor='#1a1a1a', showgrid=True, zeroline=False, title='Gold (USD/oz)', color='#ffd700')
        layout['yaxis2'] = dict(
            overlaying='y', side='right', autorange='reversed',
            showgrid=False, zeroline=False,
            title='TIPS % (inverted)', color='#00bfff'
        )
        layout['legend'] = dict(orientation='h', y=-0.15, font=dict(size=10))
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        oil_df = oil.dropna().reset_index()
        oil_df.columns = ['Date', 'WTI (USD/bbl)']
        fig = make_line_chart(oil_df, 'Date', 'WTI (USD/bbl)', color='#ffd700',
                              title='WTI CRUDE OIL — Inflation proxy', gold=True)
        st.plotly_chart(fig, use_container_width=True)

    # --- SIGNAL SUMMARY ---
    st.divider()
    st.markdown("<h3 style='font-family:monospace; color:#ffd700; font-size:0.85rem; letter-spacing:4px;'>MACRO SIGNAL SUMMARY · XAUUSD</h3>", unsafe_allow_html=True)

    signals = [
        ("10Y TIPS REAL YIELD", latest_tips, tips_signal,
         "Primary driver. Below 0% = strong structural gold bid. Above 1.5% = headwind."),
        ("DXY DOLLAR INDEX", latest_dxy, dxy_signal,
         "~-0.85 correlation with gold. Dollar weakness = gold tailwind. Watch for DXY bounces."),
        ("GOLD / SILVER RATIO", latest_gsr, gsr_signal,
         "Above 90 = extreme fear bid, risk of mean reversion. Below 70 = risk appetite, momentum."),
        ("10Y BREAKEVEN INFLATION", latest_breakeven_g, be_signal,
         "Rising breakevens compress real yields. Above 2.5% = inflationary, gold supportive."),
    ]

    signal_colors = {
        "BULLISH": "#00ff88", "BEARISH": "#ff3333", "NEUTRAL": "#888888",
        "FEAR BID": "#ffd700", "INFLATIONARY": "#00ff88",
        "BELOW TARGET": "#ff3333", "ON TARGET": "#888888",
        "RESTRICTIVE": "#ff3333",
    }

    for name, value, sig, desc in signals:
        color = signal_colors.get(sig, "#888888")
        st.markdown(f"""
            <div style="display:flex; align-items:flex-start; gap:12px; padding:10px 0;
                        border-bottom: 0.5px solid #1a1a1a;">
                <div style="width:10px; height:10px; border-radius:50%; background:{color};
                            margin-top:4px; flex-shrink:0;"></div>
                <div>
                    <span style="font-family:monospace; font-size:0.75rem; color:#ffd700;">{name}</span>
                    <span style="font-family:monospace; font-size:0.75rem; color:#888; margin-left:8px;">{value}</span>
                    <span style="font-family:monospace; font-size:0.75rem; font-weight:bold;
                                 color:{color}; margin-left:8px;">· {sig}</span>
                    <p style="font-family:monospace; font-size:0.7rem; color:#555; margin:2px 0 0;">{desc}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
