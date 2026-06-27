import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import base64
import os

# Configuration de la page
st.set_page_config(page_title="Dashboard Productivité Hôpital", layout="wide", initial_sidebar_state="expanded")

# --- FONCTION DE CHARGEMENT D'IMAGE LOCALE ---
def get_base64_image(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

IMG_BASE64 = get_base64_image("hopital.png")

# --- SYSTÈME DE LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def login():
    # CSS pour le fond d'écran du Login
    st.markdown(f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background: url("data:image/png;base64,{IMG_BASE64}") no-repeat center center fixed !important;
            background-size: cover !important;
        }}
        header {{ background: transparent !important; }}
        div[data-testid="stForm"] {{
            background-color: rgba(255, 255, 255, 0.94);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0px 4px 25px rgba(0, 0, 0, 0.4);
            margin-top: 60px;
        }}
        .login-title {{
            color: #1E3A8A;
            text-shadow: 2px 2px 10px rgba(255, 255, 255, 0.5);
            text-align: center;
            font-weight: bold;
            font-size: 2.3rem;
            margin-bottom: 15px;
        }}
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h2 class='login-title'>🏥 Hôpital Al-Ghazali - Connexion</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form(key='login_form'):
            username = st.text_input("Identifiant")
            password = st.text_input("Mot de passe", type="password")
            submit_button = st.form_submit_button(label="Se connecter")
            
            if submit_button:
                if username == "hanane.hopital" and password == "Hopital@2026":
                    st.session_state['logged_in'] = True
                    st.rerun()
                else:
                    st.error("Identifiant ou mot de passe incorrect.")

if not st.session_state['logged_in']:
    login()
else:
    # --- STYLE APRÈS LE LOGIN (FOND ATTÉNUÉ) ---
    st.markdown(f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background: linear-gradient(rgba(255, 255, 255, 0.90), rgba(255, 255, 255, 0.90)), 
                        url("data:image/png;base64,{IMG_BASE64}") no-repeat center center fixed !important;
            background-size: cover !important;
        }}
        header {{ background: transparent !important; }}
        div[data-testid="stSidebar"] {{ background-color: rgba(240, 242, 246, 0.95); }}
        </style>
    """, unsafe_allow_html=True)
    
    # --- CHARGEMENT ET NETTOYAGE DES DONNÉES ---
    @st.cache_data
    def load_and_clean_data():
        filepath = "Hanane_Lamseddek_Filali_Dashboard_Productivite_Hopital.csv"
        df_raw = pd.read_csv(filepath)
        df_clean = df_raw.copy()
        
        nb_doublons = df_clean.duplicated().sum()
        nb_manquants = df_clean.isna().sum().sum()
        
        df_clean['date'] = pd.to_datetime(df_clean['date'], errors='coerce').dt.tz_localize(None)
        df_clean = df_clean.drop_duplicates()
        
        if 'service' in df_clean.columns:
            df_clean['service'] = df_clean['service'].astype(str).str.strip()
        
        if 'satisfaction_patient_pct' in df_clean.columns:
            df_clean['satisfaction_patient_pct'] = df_clean['satisfaction_patient_pct'].fillna(df_clean['satisfaction_patient_pct'].median())
        if 'cout_service_mad' in df_clean.columns:
            df_clean['cout_service_mad'] = df_clean['cout_service_mad'].fillna(df_clean['cout_service_mad'].median())
        
        if 'temps_attente_moy_min' in df_clean.columns:
            med_attente = df_clean[df_clean['temps_attente_moy_min'] < 300]['temps_attente_moy_min'].median()
            df_clean.loc[df_clean['temps_attente_moy_min'] >= 300, 'temps_attente_moy_min'] = med_attente
            
        return df_raw, df_clean, nb_doublons, nb_manquants

    try:
        df_raw, df_clean, nb_doublons, nb_manquants = load_and_clean_data()
    except Exception as e:
        st.error(f"Erreur lors du chargement du fichier CSV : {e}")
        st.stop()

    # --- BARRE LATÉRALE ---
    st.sidebar.title("Filtres de l'Application")
    all_services = sorted(df_clean['service'].unique().tolist())
    
    selected_services = st.sidebar.multiselect("Sélectionner les Services", all_services, default=[])
    
    min_date = df_clean['date'].min().date()
    max_date = df_clean['date'].max().date()
    
    user_dates = st.sidebar.date_input("Période d'analyse", [min_date, max_date], min_value=min_date, max_value=max_date)
    
    if isinstance(user_dates, (list, tuple)) and len(user_dates) == 2:
        start_date, end_date = user_dates
    else:
        start_date = user_dates[0] if isinstance(user_dates, (list, tuple)) else user_dates
        end_date = max_date
        
    satisfaction_min = st.sidebar.slider("Pourcentage de Satisfaction minimal (%)", 0.0, 100.0, 0.0, step=5.0)

    if st.sidebar.button("Se déconnecter"):
        st.session_state['logged_in'] = False
        st.rerun()

    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🏥 Suivi de la Productivité Hospitalière</h1>", unsafe_allow_html=True)
    st.markdown("**Analyste en charge :** Hanane Lamseddek Filali")
    st.write("---")

    # --- AFFICHAGE CONDITIONNEL ---
    if not selected_services:
        st.info("ℹ️ Veuillez sélectionner un ou plusieurs services dans le filtre de la barre latérale pour afficher le tableau de bord.")
        st.progress(0)
    else:
        start_datetime = pd.Timestamp(start_date)
        end_datetime = pd.Timestamp(end_date)

        df_filtered = df_clean[
            (df_clean['service'].isin(selected_services)) &
            (df_clean['date'] >= start_datetime) &
            (df_clean['date'] <= end_datetime) &
            (df_clean['satisfaction_patient_pct'] >= satisfaction_min)
        ]

        if df_filtered.empty:
            st.warning("⚠️ Aucun résultat disponible pour cette sélection. Ajustez vos filtres.")
        else:
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📊 Vue Globale & KPI", 
                "📈 Analyse Détaillée", 
                "⚙️ Qualité des Données", 
                "📋 Extraction & Données", 
                "💡 Recommandations"
            ])

            with tab1:
                st.markdown("### 📈 Indicateurs Clés de Performance (KPI)")
                col1, col2, col3, col4 = st.columns(4)
                
                total_patients = int(df_filtered['patients_accueillis'].sum())
                col1.metric("👥 Total Patients Accueillis", f"{total_patients:,}")
                
                total_actes = df_filtered['actes_realises'].sum() if 'actes_realises' in df_filtered.columns else 0
                total_personnel = df_filtered['personnel_present'].sum() if 'personnel_present' in df_filtered.columns else 1
                prod_par_agent = total_actes / total_personnel if total_personnel > 0 else 0
                col2.metric("⚙️ Productivité par Agent", f"{prod_par_agent:.2f} actes/agent")
                
                avg_wait = df_filtered['temps_attente_moy_min'].mean()
                col3.metric("⏱️ Temps d'Attente Moyen", f"{avg_wait:.1f} min")
                
                avg_occ = df_filtered['taux_occupation_lits_pct'].mean()
                col4.metric("🛏️ Occupation Moyenne", f"{avg_occ:.1f} %")
                
                st.write("") 
                col5, col6, col7 = st.columns(3)
                
                avg_sat = df_filtered['satisfaction_patient_pct'].mean()
                col5.metric("⭐ Satisfaction Moyenne", f"{avg_sat:.1f} %")
                
                total_incidents = int(df_filtered['incidents_graves'].sum()) if 'incidents_graves' in df_filtered.columns else 0
                col6.metric("🚨 Total Incidents", f"{total_incidents}")
                
                total_marge = df_filtered['marge_service_mad'].sum() if 'marge_service_mad' in df_filtered.columns else 0
                col7.metric("💰 Marge Service", f"{total_marge:,.2f} MAD")
                
                st.write("---")

                df_trend = df_filtered.resample('ME', on='date')['patients_accueillis'].sum().reset_index()
                fig_trend = px.line(df_trend, x='date', y='patients_accueillis', title="Évolution mensuelle des admissions (Nombre total de patients)", markers=True)
                st.plotly_chart(fig_trend, use_container_width=True)

            with tab2:
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    top_services = df_filtered.groupby('service')['patients_accueillis'].sum().reset_index()
                    fig_top = px.bar(top_services, x='patients_accueillis', y='service', orientation='h', title="Volume total de patients par service")
                    st.plotly_chart(fig_top, use_container_width=True)
                
                with col_g2:
                    fig_scatter = px.scatter(df_filtered, x='taux_occupation_lits_pct', y='temps_attente_moy_min', color='service', title="Relation : Taux d'occupation vs Temps d'attente")
                    st.plotly_chart(fig_scatter, use_container_width=True)

                st.markdown("#### 🌡️ Matrice de Corrélation Numérique")
                fig_heat, ax = plt.subplots(figsize=(8, 4))
                num_cols = ['patients_accueillis', 'personnel_present', 'actes_realises', 'temps_attente_moy_min', 'taux_occupation_lits_pct', 'satisfaction_patient_pct', 'marge_service_mad']
                available_cols = [c for c in num_cols if c in df_filtered.columns]
                sns.heatmap(df_filtered[available_cols].corr(), annot=True, cmap="coolwarm", fmt=".2f", ax=ax)
                st.pyplot(fig_heat)

            with tab3:
                st.metric("🔄 Doublons Identifiés & Supprimés", nb_doublons)
                st.metric("❌ Valeurs Manquantes Imputées (Toutes colonnes)", nb_manquants)

            with tab4:
                st.dataframe(df_filtered)
                csv_data = df_filtered.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Télécharger les données filtrées en CSV", data=csv_data, file_name="Extraction_Productivite_Hopital.csv", mime='text/csv')

            with tab5:
                st.subheader("💡 Recommandations Métier")
                st.markdown("""
                1. **Optimisation des plannings** : Ajuster le nombre de personnel présent en fonction des hausses prévisibles du taux d'occupation pour réduire le temps d'attente moyen.
                2. **Suivi de la satisfaction** : Mettre en place des actions ciblées dans les services où la satisfaction descend en dessous de 70%.
                """)