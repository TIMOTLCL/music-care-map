import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Music Care Map")

# COLLE TON LIEN CSV GOOGLE SHEET ICI ENTRE LES GUILLEMETS
# Exemple: "https://docs.google.com/spreadsheets/d/e/2PACX.../pub?output=csv"
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS260Q3Tz1OIuDTZOu7ptoADnF26sjp3RLFOPYzylLZ77ZiP1KuA11-OzxNM6ktWkwL1qpylnWb1ZV4/pub?output=tsv"

# --- TITRE DU SITE ---
st.title("🗺️ Music Care - Suivi Commercial")

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data
def load_data():
    # On lit le fichier CSV
    data = pd.read_csv(SHEET_URL, sep="\t")
    return data

try:
    df = load_data()
    
    # --- AJOUTE CETTE LIGNE POUR VOIR LES COLONNES ---
    st.write("🕵️ COLONNES DÉTECTÉES :", df.columns.tolist())
    
    # --- FILTRES (Colonne de Gauche) ---
    with st.sidebar:
        st.header("Filtres")
        
        # Filtre par Région
        region_list = ["Toutes"] + list(df["Région"].unique())
        selected_region = st.selectbox("Choisir une région", region_list)
        
        # Filtre par Statut
        statut_list = ["Tous"] + list(df["Statut"].unique())
        selected_statut = st.selectbox("Statut Commercial", statut_list)

    # --- LOGIQUE DE FILTRAGE ---
    df_filtered = df.copy()
    
    # Si on ne choisit pas "Toutes", on filtre la région
    if selected_region != "Toutes":
        df_filtered = df_filtered[df_filtered["Région"] == selected_region]
        
    # Si on ne choisit pas "Tous", on filtre le statut
    if selected_statut != "Tous":
        df_filtered = df_filtered[df_filtered["Statut"] == selected_statut]

    # --- AFFICHAGE DES CHIFFRES CLÉS (KPI) ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Établissements visibles", len(df_filtered))
    # On nettoie la colonne CA pour enlever le signe € s'il y est et faire la somme
    # (C'est une version simplifiée, on peaufinera plus tard)
    
    # --- LA CARTE ---
    st.subheader(f"Carte : {selected_region}")
    
    # On centre la carte. Si une région est choisie, on centre sur ses points, sinon sur la France.
    if selected_region != "Toutes" and not df_filtered.empty:
        center_lat = df_filtered["Latitude"].mean()
        center_lon = df_filtered["Longitude"].mean()
        zoom = 8
    else:
        center_lat = 46.603354 # Centre France
        center_lon = 1.888334
        zoom = 6

    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)

    # On ajoute les points
    for index, row in df_filtered.iterrows():
        # Couleur selon le statut
        color = "blue"
        if row["Statut"] == "Client":
            color = "green"
        elif row["Statut"] == "Prospect":
            color = "red"
        elif row["Statut"] == "Discussion":
            color = "orange"
            
        folium.Marker(
            [row["Latitude"], row["Longitude"]],
            popup=f"<b>{row['Nom Établissement']}</b><br>Type: {row['Type']}<br>CA: {row['CA']}",
            tooltip=row["Nom"],
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(m)

    # Afficher la carte dans Streamlit
    st_folium(m, width=1200, height=600)

    # --- TABLEAU DE DONNÉES ---
    st.subheader("Détail des établissements")
    st.dataframe(df_filtered)

except Exception as e:
    st.error("Erreur ! Vérifie que ton lien Google Sheet est bon et que les colonnes (Latitude, Longitude, Région, Statut) existent bien.")
    st.write(e)
