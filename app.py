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
        return "Pas de photo"
    except: 
        return "Pas de photo"

def sauvegarder_dans_google_sheet(payload_data, script_url):
    if script_url:
        try: 
            requests.post(script_url, json=payload_data)
        except: 
            pass

# Structure standardisée des colonnes
COLONNES_STANDARDS = [
    "date", "heure", "ordre", "résultat", "RR", "zone", 
    "type divergence", "nb bougie divergence", "première bougie de l'arc", "derniere bougie de l'arc", "photo", "commentaire"
]

if "local_trades" not in st.session_state:
    st.session_state["local_trades"] = pd.DataFrame(columns=COLONNES_STANDARDS)

@st.cache_data(ttl=1)
def load_data(url):
    try:
        df_online = pd.read_csv(url)
        df_online = df_online.dropna(how='all')
        # Homogénéisation des noms de colonnes pour éviter les décalages d'accents
        if not df_online.empty:
            df_online.columns = [c.replace("premiere", "première") for c in df_online.columns]
        return df_online
    except:
        return pd.DataFrame(columns=COLONNES_STANDARDS)

df_sheet = load_data(csv_url)

# Fusion sécurisée des données distantes et locales
if not st.session_state["local_trades"].empty:
    if df_sheet.empty:
        df_raw = st.session_state["local_trades"].copy()
    else:
        df_raw = pd.concat([df_sheet, st.session_state["local_trades"]], ignore_index=True)
else:
    df_raw = df_sheet.copy() if not df_sheet.empty else pd.DataFrame(columns=COLONNES_STANDARDS)

# Traitement analytique sécurisé des dates et heures
if not df_raw.empty and "date" in df_raw.columns and len(df_raw) > 0:
    df = df_raw.copy()
    df["date_parsed"] = pd.to_datetime(df["date"], format="%d/%m/%Y", errors='coerce')
    df["date_parsed"] = df["date_parsed"].fillna(pd.to_datetime(df["date"], errors='coerce'))
    df = df.sort_values(by="date_parsed", ascending=True)
    
    jours_traduc = {
        'Monday': '1. Lundi', 'Tuesday': '2. Mardi', 'Wednesday': '3. Mercredi',
        'Thursday': '4. Jeudi', 'Friday': '5. Vendredi', 'Saturday': '6. Samedi', 'Sunday': '7. Dimanche'
    }
    df["Jour Semaine"] = df["date_parsed"].dt.day_name().map(jours_traduc).fillna("Inconnu")
    
    def calcul_tranche_1h(heure_str):
        try:
            h = int(str(heure_str).split(':')[0])
            return f"{h:02d}h - {h+1:02d}h"
        except: 
            return "Inconnu"
    df["Tranche Horaire"] = df["heure"].apply(calcul_tranche_1h)
else:
    df = pd.DataFrame(columns=COLONNES_STANDARDS + ["Jour Semaine", "Tranche Horaire"])

# --- BARRE LATÉRALE : INSERTION DE POSITION ---
st.sidebar.header("📥 Ajout de Positions")
saisie_rapide = st.sidebar.checkbox("Mode Saisie Rapide", value=True)

with st.sidebar.form(key="trade_form", clear_on_submit=True):
    trade_date = st.date_input("Date du trade", datetime.now(), format="DD/MM/YYYY")
    trade_time = st.time_input("Heure d'entrée exacte (HH:MM)", time(7, 0), step=60)
    zone_choisie = st.selectbox("Zone d'intervention", ["VA", "zone rouge", "VA H/L", "exploration", "jonction VA - VA H/L", "jonction VA H/L - exploration", "jonction VA - zone rouge"])
    uploaded_file = st.file_uploader("📷 Capture d'écran (Graphique)", type=["png", "jpg", "jpeg"])

    # Initialisation globale par défaut
    order_type = "À compléter"
    result_type = "À compléter"
    div_type = "À compléter"
    nb_candles = 0
    first_candle = "À compléter"
    last_candle_list = ["À compléter"]
    rr_value = 0.0
    comments = "Saisie rapide effectuée."

    if not saisie_rapide:
        order_type = st.radio("Ordre", ["achat", "vente"], horizontal=True)
        result_type = st.radio("Résultat", ["TP", "SL", "BE"], horizontal=True)
        div_type = st.radio("Type divergence", ["absorption", "exhaustion"], horizontal=True)
        nb_candles = st.number_input("Nb bougie divergence", min_value=1, value=3)
        first_candle = st.selectbox("Première bougie de l'arc", ["pin bar", "mèche", "corps"])
        last_candle_list = st.multiselect("Dernière bougie de l'arc", ["pin bar", "mèche", "corps", "englobante"], default=["pin bar"])
        
        if result_type == "SL": 
            rr_value = -1.0
        elif result_type == "TP": 
            rr_value = 2.0
        else: 
            rr_value = st.number_input("RR (à indiquer)", min_value=-1.0, max_value=10.0, value=0.0, step=0.1)
        comments = st.text_area("Commentaire")

    submit_button = st.form_submit_button(label="Enregistrer le Trade")

if submit_button:
    url_photo = "Pas de photo"
    if uploaded_file is not None:
        with st.spinner("Hébergement de l'image..."):
            url_photo = upload_image_to_imgbb(uploaded_file, IMGBB_API_KEY)
            
    date_fr = trade_date.strftime("%d/%m/%Y")
    heure_fr = trade_time.strftime("%H:%M")
    last_candle_str = " + ".join(last_candle_list) if last_candle_list else "Aucune"
            
    new_trade = pd.DataFrame([{
        "date": date_fr, "heure": heure_fr, "ordre": order_type, "résultat": result_type,
        "RR": float(rr_value), "zone": zone_choisie, "type divergence": div_type, "nb bougie divergence": int(nb_candles),
        "première bougie de l'arc": first_candle, "derniere bou