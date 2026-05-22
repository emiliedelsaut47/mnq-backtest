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
        div.stButton > button:first-child { background-color: #00E676; color: #000000; font-weight: bold; border: none; }
    </style>
""", unsafe_allow_html=True)

st.title("Tableau de Bord et Statistiques Avancées - MNQ")

# --- PARAMÈTRES ---
URL_SHEET = "https://docs.google.com/spreadsheets/d/1MNBfIn1HJFvpdEJbqm-QS8kn1AojNQACt5aIvsI2O_o/edit?usp=sharing"
URL_SCRIPT_WEB = "https://script.google.com/macros/s/AKfycbwUlsQYnhkdPJRkSCx6_tcGX6N4oLV1Y_NA2KG96YdiyP-KtP4_89sdmR91Vv_cvLir/exec"
IMGBB_API_KEY = "9c5db4365278c7dc8bd57965b8e7d545"

# --- FONCTIONS ---
def upload_image_to_imgbb(image_file, api_key):
    try:
        img_bytes = image_file.read()
        img_b64 = base64.b64encode(img_bytes)
        res = requests.post("https://api.imgbb.com/1/upload", data={"key": api_key, "image": img_b64})
        return res.json()["data"]["url"] if res.status_code == 200 else "Pas de photo"
    except: return "Pas de photo"

def analyser_critere(dataframe, colonne):
    stats = dataframe.groupby(colonne).agg(
        Total=('résultat', 'count'), TP=('résultat', lambda x: (x == 'TP').sum()),
        SL=('résultat', lambda x: (x == 'SL').sum()), BE=('résultat', lambda x: (x == 'BE').sum())
    ).reset_index()
    stats['Winrate'] = stats.apply(lambda r: (r['TP'] / (r['TP'] + r['SL']) * 100) if (r['TP'] + r['SL']) > 0 else 0.0, axis=1)
    stats['Label'] = stats.apply(lambda x: f"{x[colonne]}<br>WR: {x['Winrate']:.0f}%<br>TP:{x['TP']} SL:{x['SL']} BE:{x['BE']}", axis=1)
    return stats

# --- CHARGEMENT DONNÉES ---
@st.cache_data(ttl=1)
def load_data():
    csv_url = URL_SHEET.split("/edit")[0] + "/export?format=csv&gid=0"
    try:
        df = pd.read_csv(csv_url).dropna(how='all')
        df.columns = [c.replace("premiere", "première") for c in df.columns]
        return df
    except: return pd.DataFrame()

df = load_data()
if not df.empty:
    df["date_parsed"] = pd.to_datetime(df["date"], dayfirst=True, errors='coerce')
    df["Jour Semaine"] = df["date_parsed"].dt.day_name()
    df["Tranche Horaire"] = df["heure"].apply(lambda x: f"{str(x).split(':')[0]}h")

# --- SIDEBAR (SAISIE) ---
with st.sidebar.form(key="trade_form", clear_on_submit=True):
    st.header("Ajout de Positions")
    trade_date = st.date_input("Date", datetime.now())
    trade_time = st.time_input("Heure", time(7, 0))
    zone = st.selectbox("Zone", ["VA", "zone rouge", "VA H/L", "exploration"])
    ordre = st.radio("Ordre", ["achat", "vente"], horizontal=True)
    res = st.radio("Résultat", ["TP", "SL", "BE"], horizontal=True)
    rr = st.number_input("RR", value=0.0)
    submit = st.form_submit_button("Enregistrer")

if submit:
    payload = {"date": trade_date.strftime("%d/%m/%Y"), "heure": trade_time.strftime("%H:%M"), "ordre": ordre, "résultat": res, "RR": float(rr), "zone": zone}
    requests.post(URL_SCRIPT_WEB, json=payload)
    st.rerun()

# --- DASHBOARD ---
tab1, tab2 = st.tabs(["Statistiques", "Édition"])