import streamlit as st
import pandas as pd
import requests
import base64
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, time

# --- CONFIGURATION GRAPHIQUE DE LA PAGE ---
st.set_page_config(page_title="MNQ Professional Analytics", layout="wide", initial_sidebar_state="expanded")

# CSS personnalisé pour le style Dark Mode Premium
st.markdown("""
    <style>
        body { color: #ECEFF4; }
        [data-testid="stMetricValue"] { font-size: 28px; font-weight: 700; color: #00E676; }
        [data-testid="stMetricDelta"] { font-size: 16px; }
        .stTabs [data-baseweb="tab"] { font-size: 14px; font-weight: 600; padding: 10px 20px; }
        div.stButton > button:first-child { background-color: #00E676; color: #000000; font-weight: bold; border: none; }
        div.stButton > button:first-child:hover { background-color: #00B248; color: #ffffff; }
    </style>
""", unsafe_allow_html=True)

st.title("🎛️ Tableau de Bord & Statistiques Avancées — MNQ")

# -------------------------------------------------------------
# 💾 PARAMÈTRES INTÉGRÉS :
URL_SHEET = "https://docs.google.com/spreadsheets/d/1MNBfIn1HJFvpdEJbqm-QS8kn1AojNQACt5aIvsI2O_o/edit?usp=sharing"
IMGBB_API_KEY = "9c5db4365278c7dc8bd57965b8e7d545"
URL_SCRIPT_WEB = "https://script.google.com/macros/s/AKfycbwUlsQYnhkdPJRkSCx6_tcGX6N4oLV1Y_NA2KG96YdiyP-KtP4_89sdmR91Vv_cvLir/exec"
# -------------------------------------------------------------

if "docs.google.com" in URL_SHEET:
    base_url = URL_SHEET.split("/edit")[0]
    csv_url = f"{base_url}/export?format=csv&gid=0"
else:
    st.error("Veuillez entrer une URL Google Sheets valide.")
    st.stop()

def upload_image_to_imgbb(image_file, api_key):
    try:
        img_bytes = image_file.read()
        img_b64 = base64.b64encode(img_bytes)
        url = "https://api.imgbb.com/1/upload"
        payload = {"key": api_key, "image": img_b64}
        res = requests.post(url, data=payload)
        res_json = res.json()
        if res_json.get("status") == 200: 
            return res_json["data"]["url"]
        return "Erreur upload"
    except: 
        return "Erreur connexion"

def sauvegarder_dans_google_sheet(payload_data, script_url):
    if script_url:
        try: 
            requests.post(script_url, json=payload_data)
        except: 
            pass

if "local_trades" not in st.session_state:
    st.session_state["local_trades"] = pd.DataFrame(columns=[
        "date", "heure", "ordre", "résultat", "RR", "zone", 
        "type divergence", "nb bougie divergence", "première bougie de l'arc", "derniere bougie de l'arc", "photo", "commentaire"
    ])

@st.cache_data(ttl=1)
def load_data(url):
    try:
        df_online = pd.read_csv(url)
        df_online = df_online.dropna(how='all')
        return df_online
    except:
        return pd.DataFrame(columns=[
            "date", "heure", "ordre", "résultat", "RR", "zone", 
            "type divergence", "nb bougie divergence", "première bougie de l'arc", "derniere bougie de l'arc", "photo", "commentaire"
        ])

df_sheet = load_data(csv_url)

if not st.session_state["local_trades"].empty:
    df_raw = pd.concat([df_sheet, st.session_state["local_trades"]], ignore_index=True)
else:
    df_raw = df_sheet.copy()

if not df_raw.empty and "date" in df_raw.columns and len(df_raw) > 0:
    df = df_raw.copy()
    df["date_parsed"] = pd.to_datetime(df["date"], format="%d/%m/%Y", errors='coerce')
    df["date_parsed"] = df["date_parsed"].fillna