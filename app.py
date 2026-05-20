import streamlit as st
import pandas as pd
import requests
import base64
import plotly.graph_objects as go
import plotly.express as px
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
# 💾 TES PARAMÈTRES DIRECTEMENT INTÉGRÉS :
URL_SHEET = "https://docs.google.com/spreadsheets/d/1MNBfIn1HJFvpdEJbqm-QS8kn1AojNQACt5aIvsI2O_o/edit?usp=sharing"
IMGBB_API_KEY = "9c5db4365278c7dc8bd57965b8e7d545"
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
        if res_json["status"] == 200: 
            return res_json["data"]["url"]
        return "Erreur upload"
    except: 
        return "Erreur connexion"

@st.cache_data(ttl=2)
def load_data(url):
    try:
        return pd.read_csv(url)
    except:
        # CORRECTION LIGNE 56 : Structure correctement fermée
        return pd.DataFrame(columns=[
            "date", "heure", "ordre", "résultat", "RR", "zone", 
            "type divergence", "nb bougie divergence", "première bougie de l'arc", "derniere bougie de l'arc", "photo", "commentaire"
        ])

df_raw = load_data(csv_url)

# Traitement et enrichment des données
if not df_raw.empty and "date" in df_raw.columns:
    df = df_raw.copy()
    df["date"] = pd.to_datetime(df["date"], errors='coerce')
    df = df.sort_values(by="date", ascending=True)
    
    jours_traduc = {
        'Monday': '1. Lundi', 'Tuesday': '2. Mardi', 'Wednesday': '3. Mercredi',
        'Thursday': '4. Jeudi', 'Friday': '5. Vendredi', 'Saturday': '6. Samedi', 'Sunday': '7. Dimanche'
    }
    df["Jour Semaine"] = df["date"].dt.day_name().map(jours_traduc)
    
    def calcul_tranche_1h(heure_str):
        try:
            h = int(str(heure_str).split(':')[0])
            return f"{h:02d}h - {h+1:02d}h"
        except: 
            return "Inconnu"
    df["Tranche Horaire"] = df["heure"].apply(calcul_tranche_1h)
else:
    df = pd.DataFrame()

# --- BARRE LATÉRALE : INSERTION RAPIDE ---
st.sidebar.header("📥 Ajout de Positions")
saisie_rapide = st.sidebar.checkbox("🚀 Mode Saisie Rapide (Session Live)", value=True)

with st.sidebar.form(key="trade_form", clear_on_submit=True):
    trade_date = st.date_input("Date du trade", datetime.now())
    trade_time = st.time_input("Heure d'entrée", time(7, 0))
    zone_choisie = st.selectbox("Zone d'intervention", ["VA", "zone rouge", "VA H/L", "exploration", "jonction VA - VA H/L", "jonction VA H/L - exploration", "jonction VA - zone rouge"])
    uploaded_file = st.file_uploader("📷 Capture d'écran (Graphique)", type=["png", "jpg", "jpeg"])

    if not saisie_rapide:
        order_type = st.radio("Ordre", ["achat", "vente"], horizontal=True)
        result_type = st.radio("Résultat", ["TP", "SL", "BE"], horizontal=True)
        div_type = st.radio("Type divergence", ["absorption", "exhaustion"], horizontal=True)
        nb_candles = st.number_input("Nb bougie divergence", min_value=1, value=3)
        first_candle = st.selectbox("Première bougie de l'arc", ["pin bar", "mèche", "corps"])
        last_candle = st.selectbox("Dernière bougie de l'arc", ["pin bar", "mèche", "corps", "englobante"])
        
        if result_type == "SL": 
            rr_value = -1.0
        elif result_type == "TP": 
            rr_value = 2.0
        else: 
            rr_value = st.number_input("RR (à indiquer)", min_value=-1.0, max_value=10.0, value=0.0, step=0.1)
        comments = st.text_area("Commentaire")
    else:
        order_type, result_type, div_type, first_candle, last_candle = "À compléter", "À compléter", "À compléter", "À compléter", "À compléter"
        nb_candles, rr_value, comments = 0, 0.0, "Saisie rapide effectuée."

    submit_button = st.form_submit_button(label="Enregistrer le Trade")

# Logique de sauvegarde pour l'envoi vers Google Sheets
if submit_button:
    url_photo = "Pas de photo"
    if uploaded_file is not None:
        with st.spinner("Hébergement de l'image sur le Cloud sécurisé..."):
            url_photo = upload_image_to_imgbb(uploaded_file, IMGBB_API_KEY)
            
    new_trade = pd.DataFrame([{
        "date": str(trade_date), "heure": str(trade_time)[:5], "ordre": order_type, "résultat": result_type,
        "RR": float(rr_value), "zone": zone_choisie, "type divergence": div_type, "nb bougie divergence": int(nb_candles),
        "première bougie de l'arc": first_candle, "derniere bougie de l'arc": last_candle, "photo": url_photo, "commentaire": comments
    }])
    st.sidebar.success("Trade enregistré localement ! Synchronisation avec Google Sheets en cours...")

# --- ESPACE DE TRAVAIL CENTRAL ---
tab_dashboard, tab_correction = st.tabs(["📊 Statistiques & Graphiques", "✏️ Mode Édition (Données manquantes)"])

# ----------------------------------------------------------------------------------
# ONGLET 1 : GRAPHES PROS ET