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

# Transformation de l'URL pour la lecture CSV
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

# Initialisation sécurisée de l'état de session
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
    df["date_parsed"] = df["date_parsed"].fillna(pd.to_datetime(df["date"], errors='coerce'))
    df = df.sort_values(by="date_parsed", ascending=True)
    
    jours_traduc = {
        'Monday': '1. Lundi', 'Tuesday': '2. Mardi', 'Wednesday': '3. Mercredi',
        'Thursday': '4. Jeudi', 'Friday': '5. Vendredi', 'Saturday': '6. Samedi', 'Sunday': '7. Dimanche'
    }
    df["Jour Semaine"] = df["date_parsed"].dt.day_name().map(jours_traduc)
    
    def calcul_tranche_1h(heure_str):
        try:
            h = int(str(heure_str).split(':')[0])
            return f"{h:02d}h - {h+1:02d}h"
        except: 
            return "Inconnu"
    df["Tranche Horaire"] = df["heure"].apply(calcul_tranche_1h)
else:
    df = pd.DataFrame()

# --- BARRE LATÉRALE : INSERTION DE POSITION ---
st.sidebar.header("📥 Ajout de Positions")

saisie_rapide = st.sidebar.checkbox("🚀 Mode Saisie Rapide (Session Live)", value=True)

with st.sidebar.form(key="trade_form", clear_on_submit=True):
    trade_date = st.date_input("Date du trade", datetime.now(), format="DD/MM/YYYY")
    trade_time = st.time_input("Heure d'entrée exacte (HH:MM)", time(7, 0), step=60)
    zone_choisie = st.selectbox("Zone d'intervention", ["VA", "zone rouge", "VA H/L", "exploration", "jonction VA - VA H/L", "jonction VA H/L - exploration", "jonction VA - zone rouge"])
    uploaded_file = st.file_uploader("📷 Capture d'écran (Graphique)", type=["png", "jpg", "jpeg"])

    if not saisie_rapide:
        order_type = st.radio("Ordre", ["achat", "vente"], horizontal=True)
        result_type = st.radio("Résultat", ["TP", "SL", "BE"], horizontal=True)
        div_type = st.radio("Type divergence", ["absorption", "exhaustion"], horizontal=True)
        nb_candles = st.number_input("Nb bougie divergence", min_value=1, value=3)
        first_candle = st.selectbox("Première bougie de l'arc", ["pin bar", "mèche", "corps"])
        
        # MODIFICATION ICI : Remplacement par un multiselect pour la dernière bougie
        last_candle_list = st.multiselect("Dernière bougie de l'arc", ["pin bar", "mèche", "corps", "englobante"], default=["pin bar"])
        
        if result_type == "SL": 
            rr_value = -1.0
        elif result_type == "TP": 
            rr_value = 2.0
        else: 
            rr_value = st.number_input("RR (à indiquer)", min_value=-1.0, max_value=10.0, value=0.0, step=0.1)
        comments = st.text_area("Commentaire")
    else:
        order_type, result_type, div_type, first_candle, last_candle_list = "À compléter", "À compléter", "À compléter", "À compléter", ["À compléter"]
        nb_candles, rr_value, comments = 0, 0.0, "Saisie rapide effectuée."

    submit_button = st.form_submit_button(label="Enregistrer le Trade")

if submit_button:
    url_photo = "Pas de photo"
    if uploaded_file is not None:
        with st.spinner("Hébergement de l'image sur le Cloud sécurisé..."):
            url_photo = upload_image_to_imgbb(uploaded_file, IMGBB_API_KEY)
            
    date_fr = trade_date.strftime("%d/%m/%Y")
    heure_fr = trade_time.strftime("%H:%M")
    
    # Transformation de la liste en chaîne de caractères (ex: "pin bar + englobante") pour l'enregistrement
    last_candle_str = " + ".join(last_candle_list) if last_candle_list else "Aucune"
            
    new_trade = pd.DataFrame([{
        "date": date_fr, "heure": heure_fr, "ordre": order_type, "résultat": result_type,
        "RR": float(rr_value), "zone": zone_choisie, "type divergence": div_type, "nb bougie divergence": int(nb_candles),
        "première bougie de l'arc": first_candle, "derniere bougie de l'arc": last_candle_str, "photo": url_photo, "commentaire": comments
    }])
    
    st.session_state["local_trades"] = pd.concat([st.session_state["local_trades"], new_trade], ignore_index=True)
    
    if not saisie_rapide:
        payload = {
            "date": date_fr, "heure": heure_fr, "ordre": order_type, "résultat": result_type, "RR": float(rr_value),
            "zone": zone_choisie, "type_divergence": div_type, "nb_bougie_divergence": int(nb_candles),
            "premiere_bougie": first_candle, "derniere_bougie": last_candle_str, "photo": url_photo, "commentaire": comments
        }
        sauvegarder_dans_google_sheet(payload, URL_SCRIPT_WEB)
        
    st.sidebar.success(f"Trade enregistré localement ! ({date_fr} à {heure_fr})")
    st.rerun()

# --- ESPACE DE TRAVAIL CENTRAL ---
tab_dashboard, tab_correction = st.tabs(["📊 Statistiques & Graphiques", "✏️ Mode Édition (Données manquantes)"])

with tab_dashboard:
    if not df.empty and len(df) > 0:
        df_clean = df[df["résultat"] != "À compléter"].copy()
        
        st.markdown("### 🔑 Mesures de Performance Principales")
        c1, c2, c3, c4 = st.columns(4)
        
        total_valid = len(df_clean)
        tp_t = len(df_clean[df_clean["résultat"] == "TP"])
        sl_t = len(df_clean[df_clean["résultat"] == "SL"])
        wr = (tp_t / (tp_t + sl_t) * 100) if (tp_t + sl_t) > 0 else 0.0
        
        if total_valid > 0:
            df_clean["RR"] = pd.to_numeric(df_clean["RR"], errors='coerce').fillna(0)
            r_total = df_clean["RR"].sum()
        else:
            r_total = 0.0
            
        c1.metric("Positions Analysées", f"{total_valid} trades")
        c2.metric("Taux de Réussite (Win Rate)", f"{wr:.1f}%", f"{tp_t} TP / {sl_t} SL")
        
        signe = "+" if r_total >= 0 else ""
        c3.metric("RR Cumulé Total", f"{signe}{r_total:.1f} R")
        c4.metric("En attente de complétion", f"{len(df) - total_valid} trades")
        
        if total_valid > 0:
            st.markdown("---")
            st.markdown("### 📈 Progression Globale des Résultats (RR)")
            
            df_clean["RR_Cumsum"] = df_clean["RR"].cumsum()
            
            # REMISE EN PLACE DU GRAPHIQUE DE COURBE AVANCÉ
            fig_curve = go.Figure()
            fig_curve.add_trace(go.Scatter(
                x=df_clean["date_parsed"].dt.strftime('%d/%m/%Y'), 
                y=df_clean["RR_Cumsum"],
                mode='lines+markers',
                line=dict(color='#00E676', width=3),
                fill='tozeroy',
                fillcolor='rgba(0, 230, 118, 0.1)'
            ))
            fig_curve.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)', 
                height=300,
                margin=dict(l=20, r=20, t=20, b=20),
                font=dict(color='#ECEFF4')
            )
            st.plotly_chart(fig_curve, use_container_width=True)
            
            st.markdown("---")
            st.markdown("### 🎯 Analyses Précises par Paramètres")
            
            def analyser_critere(dataframe, colonne):
                stats = dataframe.groupby(colonne).agg(
                    Total=('résultat', 'count'),
                    TP=('résultat', lambda x: (x == 'TP').sum()),
                    SL=('résultat', lambda x: (x == 'SL').sum()),
                    R_Gain=('RR', 'sum')
                ).reset_index()
                stats['Winrate'] = stats.apply(lambda r: (r['TP'] / (r['TP'] + r['SL']) * 100) if (r['TP'] + r['SL']) > 0 else 0.0, axis=1)
                return stats

            sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🏹 Structure des Bougies", "⏰ Heures & Jours", "🗺️ Zones d'Intervention"])
            
            with sub_tab1:
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.markdown("**Première bougie de l'arc**")
                    df_first = analyser_critere(df_clean, "première bougie de l'arc")
                    # REMISE EN PLACE DU GRAPHIQUE EN BARRES
                    fig1 = px.bar(df_first, x="première bougie de l'arc", y='Winrate', color='R_Gain', color_continuous_scale='Greens', text_auto='.1f')
                    fig1.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ECEFF4'))
                    st.plotly_chart(fig1, use_container_width=True)
                    st.dataframe(df_first, use_container_width=True, hide_index=True)
                    
                with col_b2:
                    st.markdown("**Dernière bougie de l'arc**")
                    df_last = analyser_critere(df_clean, "derniere bougie de l'arc")
                    # REMISE EN PLACE DU GRAPHIQUE EN BARRES
                    fig2 = px.bar(df_last, x="derniere bougie de l'arc", y='Winrate', color='R_Gain', color_continuous_scale='Greens', text_auto='.1f')
                    fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ECEFF4'))
                    st.plotly_chart(fig2, use_container_width=True)
                    st.dataframe(df_last, use_container_width=True, hide_index=True)
                    
            with sub_tab2:
                col_h1, col_h2 = st.columns(2)
                with col_h1:
                    st.markdown("**Performance par Tranche Horaire (1h)**")
                    df_hour = analyser_critere(df_clean, "Tranche Horaire").sort_values(by="Tranche Horaire")
                    fig3 = px.bar(df_hour, x='Tranche Horaire', y='Winrate', color='R_Gain', color_continuous_scale='Greens')
                    fig3.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ECEFF4'))
                    st.plotly_chart(fig3, use_container_width=True)
                with col_h2:
                    st.markdown("**Performance par Jour de la Semaine**")
                    df