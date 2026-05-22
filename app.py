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

st.title("Tableau de Bord et Statistiques Avancées - MNQ")

# -------------------------------------------------------------
# PARAMÈTRES INTÉGRÉS
URL_SHEET = "https://docs.google.com/spreadsheets/d/1MNBfIn1HJFvpdEJbqm-QS8kn1AojNQACt5aIvsI2O_o/edit?usp=sharing"
IMGBB_API_KEY = "9c5db4365278c7dc8bd57965b8e7d545"
URL_SCRIPT_WEB = "https://script.google.com/macros/s/AKfycbwUlsQYnhkdPJRkSCx6_tcGX6N4oLV1Y_NA2KG96YdiyP-KtP4_89sdmR91Vv_cvLir/exec"