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
        .dataframe { font-size: 12px !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Tableau de Bord et Statistiques Avancées - MNQ")

# -------------------------------------------------------------
# PARAMÈTRES INTÉGRÉS
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
    "type divergence", "nb bougie divergence", "première bougie de l'arc", "derniere bougie de l'arc", "arc", "photo", "commentaire"
]

if "local_trades" not in st.session_state:
    st.session_state["local_trades"] = pd.DataFrame(columns=COLONNES_STANDARDS)

@st.cache_data(ttl=1)
def load_data(url):
    try:
        df_online = pd.read_csv(url)
        df_online = df_online.dropna(how='all')
        if not df_online.empty:
            df_online.columns = [c.replace("premiere", "première") for c in df_online.columns]
        return df_online
    except:
        return pd.DataFrame(columns=COLONNES_STANDARDS)

df_sheet = load_data(csv_url)

# Fusion sécurisée des données
if not st.session_state["local_trades"].empty:
    if df_sheet.empty:
        df_raw = st.session_state["local_trades"].copy()
    else:
        df_raw = pd.concat([df_sheet, st.session_state["local_trades"]], ignore_index=True)
else:
    df_raw = df_sheet.copy() if not df_sheet.empty else pd.DataFrame(columns=COLONNES_STANDARDS)

# Traitement des colonnes temporelles
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

# --- BARRE LATÉRALE ---
st.sidebar.header("Ajout de Positions")
saisie_rapide = st.sidebar.checkbox("Mode Saisie Rapide (Session Live)", value=True)

with st.sidebar.form(key="trade_form", clear_on_submit=True):
    trade_date = st.date_input("Date du trade", datetime.now(), format="DD/MM/YYYY")
    trade_time = st.time_input("Heure d'entrée exacte", time(7, 0), step=60)
    zone_choisie = st.selectbox("Zone d'intervention", ["VA", "zone rouge", "VA H/L", "exploration", "jonction VA - VA H/L", "jonction VA H/L - exploration", "jonction VA - zone rouge"])
    uploaded_file = st.file_uploader("Capture d'écran (Graphique)", type=["png", "jpg", "jpeg"])

    order_type = "À compléter"
    result_type = "À compléter"
    div_type = "À compléter"
    nb_candles = 0
    first_candle = "À compléter"
    last_candle = "À compléter"
    type_arc = "À compléter"
    rr_value = 0.0
    comments = "Saisie rapide effectuée."

    if not saisie_rapide:
        order_type = st.radio("Ordre", ["achat", "vente"], horizontal=True)
        result_type = st.radio("Résultat", ["TP", "SL", "BE"], horizontal=True)
        div_type = st.radio("Type divergence", ["absorption", "exhaustion"], horizontal=True)
        nb_candles = st.number_input("Nb bougie divergence", min_value=1, value=3)
        
        options_bougies = ["petite mèche", "grosse mèche", "pin bar", "corps", "double mèche"]
        first_candle = st.selectbox("Première bougie de l'arc", options_bougies)
        last_candle = st.selectbox("Dernière bougie de l'arc", options_bougies)
        type_arc = st.selectbox("Arc", ["bel arc", "arc écrasé"])
        
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
            
    new_trade = pd.DataFrame([{
        "date": date_fr, 
        "heure": heure_fr, 
        "ordre": order_type, 
        "résultat": result_type,
        "RR": float(rr_value), 
        "zone": zone_choisie, 
        "type divergence": div_type, 
        "nb bougie divergence": int(nb_candles),
        "première bougie de l'arc": first_candle, 
        "derniere bougie de l'arc": last_candle, 
        "arc": type_arc,
        "photo": url_photo, 
        "commentaire": comments
    }])
    
    st.session_state["local_trades"] = pd.concat([st.session_state["local_trades"], new_trade], ignore_index=True)
    
    if not saisie_rapide:
        payload = {
            "date": date_fr, 
            "heure": heure_fr, 
            "ordre": order_type, 
            "résultat": result_type, 
            "RR": float(rr_value),
            "zone": zone_choisie, 
            "type_divergence": div_type, 
            "nb_bougie_divergence": int(nb_candles),
            "premiere_bougie": first_candle, 
            "derniere_bougie": last_candle, 
            "arc": type_arc,
            "photo": url_photo, 
            "commentaire": comments
        }
        sauvegarder_dans_google_sheet(payload, URL_SCRIPT_WEB)
        
    st.sidebar.success(f"Trade enregistré localement ! ({date_fr} à {heure_fr})")
    st.rerun()

# --- ESPACE CENTRAL ---
tab_dashboard, tab_correction = st.tabs(["Statistiques & Graphiques", "Mode Édition (Données manquantes)"])

with tab_dashboard:
    if not df.empty and "résultat" in df.columns and len(df[df["résultat"] != "À compléter"]) > 0:
        df_clean = df[df["résultat"] != "À compléter"].copy()
        
        st.markdown("### 🔑 Mesures de Performance Principales")
        c1, c2, c3, c4 = st.columns(4)
        
        total_valid = len(df_clean)
        tp_t = len(df_clean[df_clean["résultat"] == "TP"])
        sl_t = len(df_clean[df_clean["résultat"] == "SL"])
        wr = (tp_t / (tp_t + sl_t) * 100) if (tp_t + sl_t) > 0 else 0.0
        
        df_clean["RR"] = pd.to_numeric(df_clean["RR"], errors='coerce').fillna(0)
        r_total = df_clean["RR"].sum()
            
        c1.metric("Positions Analysées", f"{total_valid} trades")
        c2.metric("Taux de Réussite (Win Rate)", f"{wr:.1f}%", f"↑ {tp_t} TP / {sl_t} SL")
        
        signe = "+" if r_total >= 0 else ""
        c3.metric("RR Cumulé Total", f"{signe}{r_total:.1f} R")
        c4.metric("En attente de complétion", f"{len(df) - total_valid} trades")
        
        st.markdown("---")
        st.markdown("### 📈 Progression Globale des Résultats (RR)")
        
        df_clean["RR_Cumsum"] = df_clean["RR"].cumsum()
        
        fig_curve = go.Figure()
        fig_curve.add_trace(go.Scatter(
            x=df_clean["date_parsed"].dt.strftime('%d/%m/%Y') if "date_parsed" in df_clean.columns else df_clean["date"], 
            y=df_clean["RR_Cumsum"],
            mode='lines+markers',
            line=dict(color='#00E676', width=3),
            fill='tozeroy',
            fillcolor='rgba(0, 230, 118, 0.1)'
        ))
        fig_curve.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=250,
            margin=dict(l=20, r=20, t=10, b=20), font=dict(color='#ECEFF4')
        )
        st.plotly_chart(fig_curve, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 🎯 Classement des Performances par Paramètre")
        
        def analyser_critere(dataframe, colonne):
            if dataframe.empty or colonne not in dataframe.columns:
                return pd.DataFrame()
            stats = dataframe.groupby(colonne).agg(
                Total=('résultat', 'count'),
                TP=('résultat', lambda x: (x == 'TP').sum()),
                BE=('résultat', lambda x: (x == 'BE').sum()),
                SL=('résultat', lambda x: (x == 'SL').sum()),
                R_Gain=('RR', 'sum')
            ).reset_index()
            stats['Winrate'] = stats.apply(lambda r: f"{(r['TP'] / (r['TP'] + r['SL']) * 100):.1f}%" if (r['TP'] + r['SL']) > 0 else "0.0%", axis=1)
            return stats

        # Rendu en barres verticales épurées et ultra-lisibles
        def afficher_graphique_bloc(dataframe, colonne, titre):
            stats = analyser_critere(dataframe, colonne)
            if stats.empty:
                st.info(f"Aucune donnée pour : {titre}")
                return
            
            # Tri décroissant pour mettre en avant les forces en premier
            stats = stats.sort_values(by='R_Gain', ascending=False)
            
            fig = px.bar(
                stats, 
                x=colonne, 
                y='R_Gain', 
                color='R_Gain',
                color_continuous_scale=[[0, '#FF5252'], [0.5, '#FFD740'], [1, '#00E676']],
                color_continuous_midpoint=0
            )
            
            fig.update_traces(
                texttemplate="<b>%{y:+.1f} R</b>",
                textposition='outside',
                hovertemplate="<b>%{x}</b><br>RR Cumulé: %{y:+.1f} R<extra></extra>"
            )
            
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=10, t=25, b=10),
                font=dict(color='#ECEFF4'),
                xaxis=dict(title="", tickangle=0),
                yaxis=dict(title="RR Cumulé", showgrid=True, gridcolor='rgba(232,232,232,0.05)'),
                coloraxis_showscale=False,
                height=260
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Tableau récapitulatif synchronisé juste en dessous pour le détail des métriques
            df_affiche = stats.rename(columns={colonne: "Configuration", "R_Gain": "RR Cumulé", "Total": "Trades"})
            st.dataframe(
                df_affiche[["Configuration", "RR Cumulé", "Winrate", "Trades", "TP", "BE", "SL"]],
                use_container_width=True,
                hide_index=True
            )

        sub_tab1, sub_tab2, sub_tab3 = st.tabs(["📊 Structure des Bougies & Arc", "⏰ Heures & Jours", "🗺️ Zones d'Intervention"])
        
        with sub_tab1:
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                st.markdown("#### 1ère bougie de l'arc")
                afficher_graphique_bloc(df_clean, "première bougie de l'arc", "Première bougie")
            with col_b2:
                st.markdown("#### Dernière bougie de l'arc")
                afficher_graphique_bloc(df_clean, "derniere bougie de l'arc", "Dernière bougie")
                
            st.markdown("---")
            col_b3, col_b4 = st.columns(2)
            with col_b3:
                st.markdown("#### Type d'Arc")
                afficher_graphique_bloc(df_clean, "arc", "Arc")
            with col_b4:
                st.markdown("#### Type de Divergence")
                afficher_graphique_bloc(df_clean, "type divergence", "Divergence")
                
        with sub_tab2:
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                st.markdown("#### Tranche Horaire (1h)")
                afficher_graphique_bloc(df_clean, "Tranche Horaire", "Tranche Horaire")
            with col_h2:
                st.markdown("#### Jour de la Semaine")
                afficher_graphique_bloc(df_clean, "Jour Semaine", "Jour Semaine")
                
        with sub_tab3:
            st.markdown("#### Zone d'Intervention")
            afficher_graphique_bloc(df_clean, "zone", "Zone")
            
    else:
        st.info("💡 Base de données connectée. Vos analyses de performance s'afficheront ici dès qu'une position sera complétée.")
        
    st.markdown("### 📋 Historique Général Brut")
    if not df.empty:
        df_display = df.copy()
        if "date_parsed" in df_display.columns:
            df_display = df_display.drop(columns=["date_parsed"])
        st.dataframe(df_display.sort_values(by="date", ascending=False), use_container_width=True, hide_index=True)

with tab_correction:
    st.subheader("🖍️ Analyse et enrichissement à tête reposée")
    
    if not df.empty and "résultat" in df.columns: 
        df_incomplets = df[df["résultat"] == "À compléter"]
    else: 
        df_incomplets = pd.DataFrame()
    
    if df_incomplets.empty:
        st.success("🎨 Parfait ! Tous vos trades enregistrés sont complétés.")
    else:
        liste_options = [f"Position du {r['date']} à {r['heure']} - Zone : {r['zone']} (ID: {i})" for i, r in df_incomplets.iterrows()]
        choix_trade = st.selectbox("Sélectionnez la position à analyser :", options=liste_options)
        index_reel = int(choix_trade.split("(ID: ")[1].replace(")", ""))
        trade_data = df.loc[index_reel]
        
        if trade_data["photo"] != "Pas de photo" and "http" in str(trade_data["photo"]):
            st.image(trade_data["photo"], caption="Graphique associé à la position", use_container_width=True)
            
        with st.form(key="formulaire_enrichissement_final"):
            col_u1, col_u2, col_u3 = st.columns(3)
            with col_u1:
                u_dir = st.radio("Ordre", ["achat", "vente"], horizontal=True)
                u_res = st.radio("Résultat", ["TP", "SL", "BE"], horizontal=True)
            with col_u2:
                u_sig = st.radio("Type divergence", ["absorption", "exhaustion"], horizontal=True)
                u_div = st.number_input("Nb bougie divergence", min_value=1, step=1, value=3)
            with col_u3:
                options_bougies_u = ["petite mèche", "grosse mèche", "pin bar", "corps", "double mèche"]
                u_first = st.selectbox("Première bougie de l'arc", options_bougies_u)
                u_last = st.selectbox("Dernière bougie de l'arc", options_bougies_u)
                u_arc = st.selectbox("Arc", ["bel arc", "arc écrasé"])
                
            if u_res == "SL": 
                u_rr = -1.0
            elif u_res == "TP": 
                u_rr = 2.0
            else: 
                u_rr = st.number_input("RR (à indiquer)", min_value=-1.0, value=0.0, step=0.1)
                
            u_comments = st.text_area("Commentaire", value="")
            save_button = st.form_submit_button("Valider et injecter les datas")
            
        if save_button:
            payload = {
                "date": str(trade_data["date"]), 
                "heure": str(trade_data["heure"]), 
                "ordre": u_dir, 
                "résultat": u_res, 
                "RR": float(u_rr),
                "zone": str(trade_data["zone"]), 
                "type_divergence": u_sig, 
                "nb_bougie_divergence": int(u_div),
                "premiere_bougie": u_first, 
                "derniere_bougie": u_last, 
                "arc": u_arc,
                "photo": str(trade_data["photo"]), 
                "commentaire": u_comments
            }
            with st.spinner("Synchronisation en cours..."):
                sauvegarder_dans_google_sheet(payload, URL_SCRIPT_WEB)
            
            nb_sheet_rows = len(df_sheet)
            if index_reel >= nb_sheet_rows:
                local_idx = index_reel - nb_sheet_rows
                if not st.session_state["local_trades"].empty and local_idx < len(st.session_state["local_trades"]):
                    st.session_state["local_trades"] = st.session_state["local_trades"].drop(st.session_state["local_trades"].index[local_idx]).reset_index(drop=True)
            
            st.success("🔥 Position enregistrée définitivement !")
            st.rerun()