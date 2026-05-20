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
# ⚠️ REMPLIS TES PARAMÈTRES CLOUD ICI :
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
        if res_json["status"] == 200: return res_json["data"]["url"]
        return "Erreur upload"
    except: return "Erreur connexion"

@st.cache_data(ttl=2)
def load_data(url):
    try:
        return pd.read_csv(url)
    except:
        # Correspondance exacte avec ton nouveau fichier Google Sheets
        return pd.DataFrame(columns=[
            "date", "heure", "ordre", "résultat", "RR", "zone", 
            "type divergence", "nb bougie divergence", "première bougie de l'arc", "derniere bougie de l'arc", "photo", "commentaire"
        ])

df_raw = load_data(csv_url)

# Traitement et enrichissement des données
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
        except: return "Inconnu"
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
    uploaded_file = st.sidebar.file_uploader("📷 Capture d'écran (Graphique)", type=["png", "jpg", "jpeg"])

    if not saisie_rapide:
        order_type = st.radio("Ordre", ["achat", "vente"], horizontal=True)
        result_type = st.radio("Résultat", ["TP", "SL", "BE"], horizontal=True)
        div_type = st.radio("Type divergence", ["absorption", "exhaustion"], horizontal=True)
        nb_candles = st.number_input("Nb bougie divergence", min_value=1, value=3)
        first_candle = st.selectbox("Première bougie de l'arc", ["pin bar", "mèche", "corps"])
        last_candle = st.selectbox("Dernière bougie de l'arc", ["pin bar", "mèche", "corps", "englobante"])
        
        if result_type == "SL": rr_value = -1.0
        elif result_type == "TP": rr_value = 2.0
        else: rr_value = st.number_input("RR (à indiquer)", min_value=-1.0, max_value=10.0, value=0.0, step=0.1)
        comments = st.text_area("Commentaire")
    else:
        order_type, result_type, div_type, first_candle, last_candle = "À compléter", "À compléter", "À compléter", "À compléter", "À compléter"
        nb_candles, rr_value, comments = 0, 0.0, "Saisie rapide effectuée."

    st.form_submit_button(label="Enregistrer le Trade")

# Gestion de l'enregistrement (simulée localement avant liaison cloud)
if st.session_state.get("FormSubmitter:trade_form-Enregistrer le Trade", False):
    pass 

# Note : Pour l'insertion réelle, Streamlit utilise les requêtes vers l'API Sheets.
# Ce bloc simule l'ajout pour la structure du dataframe
if 'df_raw' in locals() and not df_raw.empty:
    pass

# --- ESPACE DE TRAVAIL CENTRAL ---
tab_dashboard, tab_correction = st.tabs(["📊 Statistiques & Graphiques", "✏️ Mode Édition (Données manquantes)"])

# ----------------------------------------------------------------------------------
# ONGLET 1 : GRAPHES PROS ET STATISTIQUES
# ----------------------------------------------------------------------------------
with tab_dashboard:
    if not df.empty:
        df_clean = df[df["résultat"] != "À compléter"].copy()
        
        st.markdown("### 🔑 Mesures de Performance Principales")
        c1, c2, c3, c4 = st.columns(4)
        
        total_valid = len(df_clean)
        if total_valid > 0:
            tp_t = len(df_clean[df_clean["résultat"] == "TP"])
            sl_t = len(df_clean[df_clean["résultat"] == "SL"])
            wr = (tp_t / (tp_t + sl_t) * 100) if (tp_t + sl_t) > 0 else 0.0
            df_clean["RR"] = pd.to_numeric(df_clean["RR"], errors='coerce').fillna(0)
            r_total = df_clean["RR"].sum()
            
            c1.metric("Positions Analysées", f"{total_valid} trades")
            c2.metric("Taux de Réussite (Win Rate)", f"{wr:.1f}%", f"{tp_t} TP / {sl_t} SL")
            c3.metric("RR Cumulé Total", f"+{r_total:.1f} R" if r_total >= 0 else f"{r_total:.1f} R")
            c4.metric("En attente de complétion", f"{len(df) - total_valid} trades")
            
            st.markdown("---")
            st.markdown("### 📈 Progression Globale des Résultats (RR)")
            df_clean["RR_Cumsum"] = df_clean["RR"].cumsum()
            
            fig_curve = go.Figure()
            fig_curve.add_trace(go.Scatter(
                x=df_clean["date"].dt.strftime('%d/%m/%Y'), 
                y=df_clean["RR_Cumsum"],
                mode='lines+markers',
                line=dict(color='#00E676', width=3),
                fill='tozeroy',
                fillcolor='rgba(0, 230, 118, 0.1)'
            ))
            fig_curve.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300)
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

            sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["🏹 Structure des Bougies", "⏰ Heures & Jours", "🗺️ Zones d'Intervention", "⚡ Type Divergence"])
            
            with sub_tab1:
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.markdown("**première bougie de l'arc**")
                    df_first = analyser_critere(df_clean, "première bougie de l'arc")
                    fig = px.bar(df_first, x='première bougie de l'arc', y='Winrate', color='R_Gain', color_continuous_scale='Greens')
                    st.plotly_chart(fig, use_container_width=True)
                with col_b2:
                    st.markdown("**derniere bougie de l'arc**")
                    df_last = analyser_critere(df_clean, "derniere bougie de l'arc")
                    fig = px.bar(df_last, x='derniere bougie de l'arc', y='Winrate', color='R_Gain', color_continuous_scale='Greens')
                    st.plotly_chart(fig, use_container_width=True)
                    
            with sub_tab2:
                col_h1, col_h2 = st.columns(2)
                with col_h1:
                    df_hour = analyser_critere(df_clean, "Tranche Horaire")
                    fig = px.bar(df_hour, y='Tranche Horaire', x='Winrate', orientation='h')
                    st.plotly_chart(fig, use_container_width=True)
                with col_h2:
                    df_day = analyser_critere(df_clean, "Jour Semaine")
                    fig = px.bar(df_day, x='Jour Semaine', y='Winrate')
                    st.plotly_chart(fig, use_container_width=True)
                    
            with sub_tab3:
                df_zone = analyser_critere(df_clean, "zone")
                st.dataframe(df_zone.sort_values(by="Winrate", ascending=False), use_container_width=True, hide_index=True)
                
            with sub_tab4:
                df_sig = analyser_critere(df_clean, "type divergence")
                fig_pie = px.pie(df_sig, values='Total', names='type divergence', hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Aucun trade validé disponible pour les graphiques. Utilisez l'onglet Édition.")
            
        st.markdown("### 📋 Historique Général Brut")
        st.dataframe(df.sort_values(by="date", ascending=False), use_container_width=True)
    else:
        st.info("Base de données vide.")

# ----------------------------------------------------------------------------------
# ONGLET 2 : LE CENTRE DE CORRECTION
# ----------------------------------------------------------------------------------
with tab_correction:
    st.subheader("✏️ Analyse et enrichissement à tête reposée")
    df_incomplets = df_raw[df_raw["résultat"] == "À compléter"]
    
    if df_incomplets.empty:
        st.success("🎉 Parfait ! Tous vos trades sont complétés.")
    else:
        liste_options = [f"Position du {r['date']} à {r['heure']} — Zone : {r['zone']} (ID: {i})" for i, r in df_incomplets.iterrows()]
        choix_trade = st.selectbox("Sélectionnez la position à analyser :", options=liste_options)
        
        index_reel = int(choix_trade.split("(ID: ")[1].replace(")", ""))
        trade_data = df_raw.loc[index_reel]
        
        if trade_data["photo"] != "Pas de photo" and "http" in str(trade_data["photo"]):
            st.image(trade_data["photo"], caption=f"Graphique MNQ — {trade_data['heure']}", use_container_width=True)
            
        with st.form(key="update_form"):
            col_u1, col_u2, col_u3 = st.columns(3)
            with col_u1:
                u_dir = st.radio("Ordre", ["achat", "vente"], horizontal=True)
                u_res = st.radio("Résultat", ["TP", "SL", "BE"], horizontal=True)
            with col_u2:
                u_sig = st.radio("Type divergence", ["absorption", "exhaustion"], horizontal=True)
                u_div = st.number_input("Nb bougie divergence", min_value=1, step=1, value=3)
            with col_u3:
                u_first = st.selectbox("Première bougie de l'arc", ["pin bar", "mèche", "corps"])
                u_last = st.selectbox("Dernière bougie de l'arc", ["pin bar", "mèche", "corps", "englobante"])
                
            if u_res == "SL": u_rr = -1.0
            elif u_res == "TP": u_rr = 2.0
            else: u_rr = st.number_input("RR (à indiquer)", min_value=-1.0, value=0.0, step=0.1)
                
            u_comments = st.text_area("Commentaire", value="")
            st.form_submit_button("Valider et injecter les datas")