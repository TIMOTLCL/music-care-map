import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import unicodedata

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(layout="wide", page_title="Music Care CRM")

# --- TON LIEN GOOGLE SHEET ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS260Q3Tz1OIuDTZOu7ptoADnF26sjp3RLFOPYzylLZ77ZiP1KuA11-OzxNM6ktWkwL1qpylnWb1ZV4/pub?output=tsv"

# --- FONCTION DE NETTOYAGE DES ACCENTS (Indispensable pour les couleurs) ---
def remove_accents(input_str):
    if not isinstance(input_str, str):
        return str(input_str)
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

# --- FONCTION DE CHARGEMENT ---
@st.cache_data(ttl=60)
def load_data():
    try:
        data = pd.read_csv(SHEET_URL, sep="\t")
        
        # 1. Nettoyage des titres de colonnes
        data.columns = data.columns.str.strip()
        
        # 2. Nettoyage du CA
        if "CA" in data.columns:
            data["CA"] = data["CA"].astype(str).str.replace(",", ".").str.replace(r'[^\d.-]', '', regex=True)
            data["CA"] = pd.to_numeric(data["CA"], errors='coerce').fillna(0)

        # 3. Création colonne "Statut_Clean" pour la logique couleur
        if "Statut" in data.columns:
            data["Statut_Clean"] = data["Statut"].apply(lambda x: remove_accents(str(x)).lower().strip())
            
        return data
    except Exception as e:
        st.error(f"Erreur de lecture : {e}")
        return pd.DataFrame()

df = load_data()

# --- TITRE ---
st.title("📊 Music Care - Pilotage Commercial")

if not df.empty and "Latitude" in df.columns:
    
    # --- BARRE LATÉRALE ---
    with st.sidebar:
        st.header("🔍 Filtres")

        # 1. Région
        if "Région" in df.columns:
            region_list = ["Toutes"] + sorted(list(df["Région"].dropna().unique()))
            selected_region = st.selectbox("1. Région", region_list)
        else: selected_region = "Toutes"
        
        # 2. Département
        if "Département" in df.columns:
            if selected_region != "Toutes":
                dept_options = df[df["Région"] == selected_region]["Département"].unique()
                dept_list = ["Tous"] + sorted(list(dept_options))
            else:
                dept_list = ["Tous"] + sorted(list(df["Département"].unique()))
            selected_dept = st.selectbox("2. Département", dept_list)
        else: selected_dept = "Tous"

        # 3. Type
        if "Type" in df.columns:
            type_list = ["Tous"] + sorted(list(df["Type"].dropna().unique()))
            selected_type = st.selectbox("3. Type", type_list)
        else: selected_type = "Tous"
        
        # 4. Statut
        if "Statut" in df.columns:
            statut_list = ["Tous"] + sorted(list(df["Statut"].dropna().unique()))
            selected_statut = st.selectbox("4. Statut", statut_list)
        else: selected_statut = "Tous"

    # --- FILTRAGE ---
    df_filtered = df.copy()
    if selected_region != "Toutes": df_filtered = df_filtered[df_filtered["Région"] == selected_region]
    if selected_dept != "Tous": df_filtered = df_filtered[df_filtered["Département"] == selected_dept]
    if selected_type != "Tous": df_filtered = df_filtered[df_filtered["Type"] == selected_type]
    if selected_statut != "Tous": df_filtered = df_filtered[df_filtered["Statut"] == selected_statut]

    # --- KPI (CHIFFRES CLÉS) ---
    total_etablissements = len(df_filtered)
    total_ca = df_filtered["CA"].sum()
    
    # Calculs basés sur le "Statut_Clean" pour être précis
    nb_clients = len(df_filtered[df_filtered["Statut_Clean"].str.contains("client", na=False)])
    nb_prospects = len(df_filtered[df_filtered["Statut_Clean"].str.contains("prospect", na=False)])
    nb_discussion = len(df_filtered[df_filtered["Statut_Clean"].str.contains("discussion", na=False)])

    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🏢 Total", total_etablissements)
    col2.metric("💰 CA Total", f"{total_ca:,.0f} €".replace(",", " "))
    col3.metric("✅ Clients", nb_clients)
    col4.metric("💬 Discussion", nb_discussion)
    col5.metric("🎯 Prospects", nb_prospects)
    st.markdown("---")

    # --- CARTE ---
    col_map, col_details = st.columns([2, 1])

    with col_map:
        st.subheader(f"Carte : {selected_region}")
        if not df_filtered.empty:
            center_lat = df_filtered["Latitude"].mean()
            center_lon = df_filtered["Longitude"].mean()
            zoom = 6
            if selected_dept != "Tous": zoom = 10
            elif selected_region != "Toutes": zoom = 8
        else: center_lat, center_lon, zoom = 46.6, 1.8, 6

        # Fond de carte 'CartoDB positron' pour un look pro et épuré
        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles="CartoDB positron")

        # BOUCLE D'AFFICHAGE DES POINTS (SANS CLUSTER)
        for index, row in df_filtered.iterrows():
            statut_clean = str(row.get("Statut_Clean", ""))
            
            # --- COULEURS DÉFINITIVES ---
            if "client" in statut_clean:
                color = "#2ecc71"  # VERT
                radius = 6         # Un peu plus gros pour les clients
                z_index = 1000     # Pour qu'ils s'affichent au-dessus des autres
            elif "discussion" in statut_clean:
                color = "#3498db"  # BLEU
                radius = 5
                z_index = 900
            elif "refuse" in statut_clean:
                color = "#9b59b6"  # VIOLET
                radius = 4
                z_index = 100
            elif "resilie" in statut_clean:
                color = "#e74c3c"  # ROUGE
                radius = 5
                z_index = 500
            elif "prospect" in statut_clean:
                color = "#95a5a6"  # GRIS
                radius = 4
                z_index = 100
            else:
                color = "#95a5a6"  # GRIS par défaut
                radius = 4
                z_index = 100

            # Contenu Info-bulle
            nom = row.get('Nom Établissement', 'Inconnu')
            statut_officiel = row.get('Statut', '-')
            type_etab = row.get('Type', '-')
            ca = row.get('CA', 0)

            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=radius,
                color=color,
                weight=1,          # Bordure fine
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                popup=f"<b>{nom}</b><br>{type_etab}<br>Statut: {statut_officiel}<br>CA: {ca} €",
                tooltip=nom,
                z_index_offset=z_index 
            ).add_to(m)

        st_folium(m, width="100%", height=600)

    # --- DÉTAILS ---
    with col_details:
        st.subheader("Détails")
        if selected_region != "Toutes" and selected_dept == "Tous":
            st.caption("CA par Département")
            ca_by_dept = df_filtered.groupby("Département")["CA"].sum().sort_values(ascending=False)
            st.dataframe(ca_by_dept, use_container_width=True)
        
        st.dataframe(df_filtered[["Nom Établissement", "Ville", "Statut", "CA"]], hide_index=True, use_container_width=True)

else:
    st.warning("⚠️ Données non chargées. Vérifie ton fichier.")
