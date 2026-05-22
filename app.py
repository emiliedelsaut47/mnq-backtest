import streamlit as st
import pandas as pd
import requests
import base64
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, time

# --- CONFIGURATION GRAPHIQUE ---
st.set_page_config(page_title="MNQ Professional Analytics", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        body { color: #ECEFF4; }
        [data-testid="stMetricValue"] { font-size: 28px; font-weight: 700; color: #00E676; }
        .stTabs [data-baseweb="tab"] { font-size: 14px; font-weight: 600; padding: 10px 20px; }
        div.stButton > button:first-child { background-color: #00E676; color: #000000; font-weight: bold; border: none; }
    </style>
""", unsafe_allow_html=True)

st.title("🎛️ Tableau de Bord & Statistiques Avancées — MNQ")

# 💾 CONFIGURATION
URL_SHEET = "https://docs.google.com/spreadsheets/d/1MNBfIn1HJFvpdEJbqm-QS8kn1AojNQACt5aIvsI2O_o/edit?usp=sharing"
IMGBB_API_KEY = "9c5db4365278c7dc8bd57965b8e7d545"
URL_SCRIPT_WEB = "https://script.google.com/macros/s/AKfycbwUlsQYnhkdPJRkSCx6_tcGX6N4oLV1Y_NA2KG96YdiyP-KtP4_89sdmR91Vv_cvLir/exec"

def load_data(url):
    try:
        base_url = url.split("/edit")[0]
        csv_url = f"{base_url}/export?format=csv&gid=0"
        return pd.read_csv(csv_url).dropna(how='all')
    except:
        return pd.DataFrame()

df = load_data(URL_SHEET)

# --- SIDEBAR ---
st.sidebar.header("📥 Ajout de Positions")
with st.sidebar.form(key="trade_form", clear_on_submit=True):
    trade_date = st.date_input("Date", datetime.now())
    trade_time = st.time_input("Heure", time(7, 0))
    zone = st.selectbox("Zone", ["VA", "zone rouge", "VA H/L", "exploration"])
    ordre = st.radio("Ordre", ["achat", "vente"], horizontal=True)
    result = st.radio("Résultat", ["TP", "SL", "BE"], horizontal=True)
    rr = st.number_input("RR", value=0.0)
    div_type = st.radio("Divergence", ["absorption", "exhaustion"], horizontal=True)
    nb_bougies = st.number_input("Nb bougies", value=3)
    first_c = st.selectbox("1ère bougie", ["petite mèche", "grosse mèche", "pin bar", "corps", "double mèche"])
    last_c = st.selectbox("Dernière bougie", ["petite mèche", "grosse mèche", "pin bar", "corps", "double mèche"])
    arc = st.selectbox("Arc", ["bel arc", "arc écrasé"])
    submit = st.form_submit_button("Enregistrer le Trade")

if submit:
    payload = {
        "date": trade_date.strftime("%d/%m/%Y"), "heure": trade_time.strftime("%H:%M"),
        "ordre": ordre, "résultat": result, "RR": float(rr), "zone": zone,
        "type_divergence": div_type, "nb_bougie_divergence": int(nb_bougies),
        "premiere_bougie": first_c, "derniere_bougie": last_c, "arc": arc
    }
    requests.post(URL_SCRIPT_WEB, json=payload)
    st.sidebar.success("Enregistré !")
    st.rerun()

# --- DASHBOARD ---
if not df.empty:
    df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y")
    
    col1, col2, col3, col4 = st.columns(4)
    tp = len(df[df["résultat"] == "TP"])
    sl = len(df[df["résultat"] == "SL"])
    col1.metric("Total", len(df))
    col2.metric("Winrate", f"{(tp/(tp+sl)*100 if (tp+sl)>0 else 0):.1f}%")
    col3.metric("RR Total", f"{df['RR'].sum():.1f} R")
    col4.metric("Trades", len(df))

    st.subheader("📈 Répartition")
    c1, c2 = st.columns(2)
    with c1:
        fig1 = px.pie(df, names='résultat', title="Résultats (TP/SL/BE)", hole=0.4)
        st.plotly_chart(fig1, use_container_