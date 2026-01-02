import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster # L'outil magique pour la vitesse

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(layout="wide", page_title="Music Care CRM")

# --- TON LIEN GOOGLE SHEET ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS260Q3Tz1OIuDTZOu7ptoADnF26sjp3RLFOPYzylLZ77ZiP1KuA11-OzxNM6ktWkwL1qpylnWb1ZV4/pub?output=tsv"

# --- FONCTION DE CHARGEMENT ---
@st.cache_data(ttl=300)
def load_data():
    try:
        data = pd.read_csv(SHEET_URL, sep="\t")
        
        # Nettoyage du CA "Blindé"
        if "CA" in data.columns:
            data["CA"] = data["CA"].astype(str)
            data["CA"] = data["CA"].str.replace(",", ".")
            data["CA"] = data["CA"].str.replace(r'[^\d.-]', '', regex=True)
            data["CA"] = pd.to_numeric(data["CA"], errors='coerce').fillna(0)
            
        return data
    except Exception as e:
        st.error("Erreur de lecture du fichier.")
        return pd.DataFrame()

df = load_data()

# --- TITRE ---
st.title("📊 Music Care - Pilotage Commercial")

if not df.empty and "Latitude" in df.columns:
    
    # --- BARRE LATÉRALE (FILTRES) ---
    with st.sidebar:
        st.header("🔍 Filtres")
        
        # 1. Région
        if "Région" in df.columns:
            region_list = ["Toutes"] + sorted(list(df["Région"].dropna().unique()))
            selected_region = st.selectbox("1. Région", region_list)
        else:
            selected_region = "Toutes"
        
        # 2. Département (Dynamique)
        if "Département" in df.columns:
            if selected_region != "Toutes":
                dept_options = df[df["Région"] == selected_region]["Département"].unique()
                dept_list = ["Tous"] + sorted(list(dept_options))
            else:
                dept_list = ["Tous"] + sorted(list(df["Département"].unique()))
            selected_dept = st.selectbox("2. Département", dept_list)
        else:
            selected_dept = "Tous"

        # 3. Type
        if "Type" in df.columns:
            type_list = ["Tous"] + sorted(list(df["Type"].dropna().unique()))
            selected_type = st.selectbox("3. Type d'établissement", type_list)
        else:
            selected_type = "Tous"
        
        # 4. Statut
        if "Statut" in df.columns:
            statut_list = ["Tous"] + sorted(list(df["Statut"].dropna().unique()))
            selected_statut = st.selectbox("4. Statut", statut_list)
        else:
            selected_statut = "Tous"

    # --- FILTRAGE DES DONNÉES ---
    df_filtered = df.copy()
    
    if selected_region != "Toutes":
        df_filtered = df_filtered[df_filtered["Région"] == selected_region]
    if selected_dept != "Tous":
        df_filtered = df_filtered[df_filtered["Département"] == selected_dept]
    if selected_type != "Tous":
        df_filtered = df_filtered[df_filtered["Type"] == selected_type]
    if selected_statut != "Tous":
        df_filtered = df_filtered[df_filtered["Statut"] == selected_statut]

    # --- DASHBOARD (KPI) ---
    total_etablissements = len(df_filtered)
    total_ca = df_filtered["CA"].sum()
    
    # Calcul des statuts pour KPI (exemple simplifié)
    nb_clients = len(df_filtered[df_filtered["Statut"].astype(str).str.contains("Client", case=False, na=False)])
    nb_prospects = len(df_filtered[df_filtered["Statut"].astype(str).str.contains("Prospect", case=False, na=False)])

    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🏢 Total affiché", total_etablissements)
    col2.metric("💰 CA Total", f"{total_ca:,.0f} €".replace(",", " "))
    col3.metric("✅ Clients", nb_clients)
    col4.metric("🎯 Prospects", nb_prospects)
    st.markdown("---")

    # --- CARTE INTERACTIVE ---
    col_map, col_details = st.columns([2, 1])

    with col_map:
        st.subheader(f"Carte : {selected_region}")
        
        # Centrage intelligent
        if not df_filtered.empty:
            center_lat = df_filtered["Latitude"].mean()
            center_lon = df_filtered["Longitude"].mean()
            if selected_dept != "Tous":
                zoom = 10
            elif selected_region != "Toutes":
                zoom = 8
            else:
                zoom = 6
        else:
            center_lat, center_lon, zoom = 46.6, 1.8, 6

        # Affichage carte
        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles="CartoDB positron")

        # --- OPTIMISATION : CLUSTERING ---
        # On crée un groupe de clusters pour gérer la fluidité avec 2100 points
        marker_cluster = MarkerCluster().add_to(m)

        for index, row in df_filtered.iterrows():
            statut = str(row["Statut"]).lower()
            
            # --- NOUVELLE LOGIQUE DES COULEURS ---
            if "Client" in statut:
                color = "#2ecc71"  # VERT (Client)
                radius = 8
            elif "Discussion" in statut:
                color = "#3498db"  # BLEU (Discussion)
                radius = 7
            elif "Refusé" in statut or "refuse" in statut:
                color = "#9b59b6"  # VIOLET (Refusé)
                radius = 6
            elif "Résilié" in statut or "resilie" in statut:
                color = "#e74c3c"  # ROUGE (Résilié)
                radius = 6
            elif "Prospect" in statut:
                color = "#95a5a6"  # GRIS (Prospect)
                radius = 6
            else:
                color = "#95a5a6"  # GRIS par défaut
                radius = 6

            # On ajoute les points AU CLUSTER et non directement à la carte
            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=radius,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                popup=f"<b>{row['Nom Établissement']}</b><br>{row['Type']}<br>Statut: {row['Statut']}<br>CA: {row['CA']} €",
                tooltip=row["Nom Établissement"]
            ).add_to(marker_cluster)

        st_folium(m, width="100%", height=600)

    # --- DÉTAILS ---
    with col_details:
        st.subheader("Détails")
        if selected_region != "Toutes" and selected_dept == "Tous":
            st.caption("CA par Département")
            ca_by_dept = df_filtered.groupby("Département")["CA"].sum().sort_values(ascending=False)
            st.dataframe(ca_by_dept, use_container_width=True)
        
        st.caption("Liste filtrée")
        st.dataframe(
            df_filtered[["Nom Établissement", "Ville", "Statut", "CA"]], 
            hide_index=True,
            use_container_width=True
        )

else:
    st.warning("⚠️ Données non chargées ou colonnes GPS manquantes.")
