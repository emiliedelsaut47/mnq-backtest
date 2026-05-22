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
        try: requests.post(script_url, json=payload_data)
        except: pass

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
    df["Jour Semaine"] = df["date_parsed"].dt.day_name().map(jours_traduc).fillna("Inconnu")
    
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
        last_candle_list = st.multiselect("Dernière bougie de l'arc", ["pin bar", "mèche", "corps", "englobante"], default=["pin bar"])
        
        if result_type == "SL": rr_value = -1.0
        elif result_type == "TP": rr_value = 2.0
        else: rr_value = st.number_input("RR (à indiquer)", min_value=-1.0, max_value=10.0, value=0.0, step=0.1)
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
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300,
                margin=dict(l=20, r=20, t=20, b=20), font=dict(color='#ECEFF4')
            )
            st.plotly_chart(fig_curve, use_container_width=True)
            
            st.markdown("---")
            st.markdown("### 🎯 Analyses Précises par Paramètres")
            
            def analyser_critere(dataframe, colonne):
                if dataframe.empty or colonne not in dataframe.columns:
                    return pd.DataFrame()
                stats = dataframe.groupby(colonne).agg(
                    Total=('résultat', 'count'),
                    TP=('résultat', lambda x: (x == 'TP').sum()),
                    SL=('résultat', lambda x: (x == 'SL').sum()),
                    BE=('résultat', lambda x: (x == 'BE').sum()),
                    R_Gain=('RR', 'sum')
                ).reset_index()
                stats['Winrate'] = stats.apply(lambda r: (r['TP'] / (r['TP'] + r['SL']) * 100) if (r['TP'] + r['SL']) > 0 else 0.0, axis=1)
                return stats

            def generer_camembert_rich(dataframe, colonne_nom):
                df_stats = analyser_critere(dataframe, colonne_nom)
                if df_stats.empty:
                    return None
                
                # Construction explicite de la chaîne textuelle interne requise
                df_stats['label_interne'] = df_stats.apply(
                    lambda r: f"<b>{r[colonne_nom]}</b><br>{r['Winrate']:.1f}% WR<br>({r['TP']}TP / {r['SL']}SL / {r['BE']}BE)", axis=1
                )
                
                fig = px.pie(
                    df_stats, 
                    names=colonne_nom, 
                    values='Total'
                )
                
                fig.update_traces(
                    text=df_stats['label_interne'],
                    textinfo='text',
                    textposition='inside',
                    insidetextorientation='horizontal',
                    marker=dict(line=dict(color='#1E1E1E', width=2))
                )
                
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#ECEFF4', size=12),
                    showlegend=True,
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=380
                )
                return fig

            sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🏹 Structure des Bougies", "⏰ Heures & Jours", "🗺️ Zones d'Intervention"])
            
            with sub_tab1:
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.markdown("**Première bougie de l'arc**")
                    g1 = generer_camembert_rich(df_clean, "première bougie de l'arc")
                    if g1: st.plotly_chart(g1, use_container_width=True)
                    df_first = analyser_critere(df_clean, "première bougie de l'arc")
                    st.dataframe(df_first, use_container_width=True, hide_index=True)
                    
                with col_b2:
                    st.markdown("**Dernière bougie de l'arc**")
                    g2 = generer_camembert_rich(df_clean, "derniere bougie de l'arc")
                    if g2: st.plotly_chart(g2, use_container_width=True)
                    df_last = analyser_critere(df_clean, "derniere bougie de l'arc")
                    st.dataframe(df_last, use_container_width=True, hide_index=True)
                    
            with sub_tab2:
                col_h1, col_h2 = st.columns(2)
                with col_h1:
                    st.markdown("**Performance par Tranche Horaire (1h)**")
                    g3 = generer_camembert_rich(df_clean, "Tranche Horaire")
                    if g3: st.plotly_chart(g3, use_container_width=True)
                    df_hour = analyser_critere(df_clean, "Tranche Horaire").sort_values(by="Tranche Horaire")
                    st.dataframe(df_hour, use_container_width=True, hide_index=True)
                with col_h2:
                    st.markdown("**Performance par Jour de la Semaine**")
                    g4 = generer_camembert_rich(df_clean, "Jour Semaine")
                    if g4: st.plotly_chart(g4, use_container_width=True)
                    df_day = analyser_critere(df_clean, "Jour Semaine").sort_values(by="Jour Semaine")
                    st.dataframe(df_day, use_container_width=True, hide_index=True)
                    
            with sub_tab3:
                st.markdown("**Performance par Zone d'Intervention**")
                g5 = generer_camembert_rich(df_clean, "zone")
                if g5: st.plotly_chart(g5, use_container_width=True)
                df_zone = analyser_critere(df_clean, "zone")
                st.dataframe(df_zone.sort_values(by="Winrate", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("💡 Vos données sont connectées ! Remplissez les caractéristiques manquantes de votre position ci-dessus dans l'onglet 'Mode Édition' pour voir vos graphiques.")
            
        st.markdown("### 📋 Historique Général Brut")
        df_display = df.copy()
        if "date_parsed" in df_display.columns:
            df_display = df_display.drop(columns=["date_parsed"])
        st.dataframe(df_display.sort_values(by="date", ascending=False), use_container_width=True)
    else:
        st.info("ℹ️ Base de données actuellement vide ou en attente de synchronisation. Ajoutez un trade dans la barre latérale.")

with tab_correction:
    st.subheader("✏️ Analyse et enrichissement à tête reposée")
    
    # Correction de l'assignation de df_incomplets pour éviter les NameError
    if not df.empty and "résultat" in df.columns: 
        df_incomplets = df[df["résultat"] == "À compléter"]
    else: 
        df_incomplets = pd.DataFrame()
    
    if df_incomplets.empty:
        st.success("🎉 Parfait ! Tous vos trades enregistrés sont complétés.")
    else:
        liste_options = [f"Position du {r['date']} à {r['heure']} — Zone : {r['zone']} (ID: {i})" for i, r in df_incomplets.iterrows()]
        choix_trade = st.selectbox("Sélectionnez la position à analyser :", options=liste_options)
        index_reel = int(choix_trade.split("(ID: ")[1].replace(")", ""))
        trade_data = df.loc[index_reel]
        
        if trade_data["photo"] != "Pas de photo" and "http" in str(trade_data["photo"]):
            st.image(trade_data["photo"], caption=f"Graphique MNQ — {trade_data['heure']}", use_container_width=True)
            
        # Formulaire principal avec son st.form_submit_button bien rattaché à la racine
        with st.form(key="update_form_fixed_v2"):
            col_u1, col_u2, col_u3 = st.columns(3)
            with col_u1:
                u_dir = st.radio("Ordre", ["achat", "vente"], horizontal=True)
                u_res = st.radio("Résultat", ["TP", "SL", "BE"], horizontal=True)
            with col_u2:
                u_sig = st.radio("Type divergence", ["absorption", "exhaustion"], horizontal=True)
                u_div = st.number_input("Nb bougie divergence", min_value=1, step=1, value=3)
            with col_u3:
                u_first = st.selectbox("Première bougie de l'arc", ["pin bar", "mèche", "corps"])
                u_last_list = st.multiselect("Dernière bougie de l'arc", ["pin bar", "mèche", "corps", "englobante"], default=["pin bar"])
                
            if u_res == "SL": u_rr = -1.0
            elif u_res == "TP": u_rr = 2.0
            else: u_rr = st.number_input("RR (à indiquer)", min_value=-1.0, value=0.0, step=0.1)
                
            u_comments = st.text_area("Commentaire", value="")
            
            save_button = st.form_submit_button("Valider et injecter les datas")
            
        if save_button:
            u_last_str = " + ".join(u_last_list) if u_last_list else "Aucune"
            payload = {
                "date": str(trade_data["date"]), "heure": str(trade_data["heure"]), "ordre": u_dir, "résultat": u_res, "RR": float(u_rr),
                "zone": str(trade_data["zone"]), "type_divergence": u_sig, "nb_bougie_divergence": int(u_div),
                "premiere_bougie": u_first, "derniere_bougie": u_last_str, "photo": str(trade_data["photo"]), "commentaire": u_comments
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