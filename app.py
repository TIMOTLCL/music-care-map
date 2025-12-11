import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(layout="wide", page_title="Music Care CRM")

# --- TON LIEN GOOGLE SHEET ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS260Q3Tz1OIuDTZOu7ptoADnF26sjp3RLFOPYzylLZ77ZiP1KuA11-OzxNM6ktWkwL1qpylnWb1ZV4/pub?output=tsv"

# --- FONCTION DE CHARGEMENT ---
# Avant c'était juste : @st.cache_data
# Maintenant, remplace par :
@st.cache_data(ttl=60)
def load_data():
    try:
        data = pd.read_csv(SHEET_URL, sep="\t")
        # Nettoyage du CA : on s'assure que c'est bien des chiffres
        if "CA" in data.columns:
            data["CA"] = data["CA"].astype(str).str.replace(" ", "").str.replace("€", "").str.replace(",", ".")
            data["CA"] = pd.to_numeric(data["CA"], errors='coerce').fillna(0)
        return data
    except Exception as e:
        st.error("Erreur de lecture du fichier.")
        return pd.DataFrame()

df = load_data()

# --- TITRE ---
st.title("📊 Music Care - Pilotage Commercial")

if not df.empty:
    
    # --- BARRE LATÉRALE (FILTRES EN ENTONNOIR) ---
    with st.sidebar:
        st.header("🔍 Filtres")
        
        # 1. Filtre RÉGION
        region_list = ["Toutes"] + sorted(list(df["Région"].unique()))
        selected_region = st.selectbox("1. Région", region_list)
        
        # 2. Filtre DÉPARTEMENT (Dépendant de la région choisie)
        if selected_region != "Toutes":
            # On ne propose que les départements de la région choisie
            dept_options = df[df["Région"] == selected_region]["Département"].unique()
            dept_list = ["Tous"] + sorted(list(dept_options))
        else:
            dept_list = ["Tous"] + sorted(list(df["Département"].unique()))
            
        selected_dept = st.selectbox("2. Département", dept_list)

        # 3. Filtre TYPE D'ÉTABLISSEMENT
        type_list = ["Tous"] + sorted(list(df["Type"].unique()))
        selected_type = st.selectbox("3. Type d'établissement", type_list)
        
        # 4. Filtre STATUT
        statut_list = ["Tous"] + sorted(list(df["Statut"].unique()))
        selected_statut = st.selectbox("4. Statut", statut_list)

    # --- APPLICATION DES FILTRES ---
    df_filtered = df.copy()
    
    if selected_region != "Toutes":
        df_filtered = df_filtered[df_filtered["Région"] == selected_region]
        
    if selected_dept != "Tous":
        df_filtered = df_filtered[df_filtered["Département"] == selected_dept]

    if selected_type != "Tous":
        df_filtered = df_filtered[df_filtered["Type"] == selected_type]

    if selected_statut != "Tous":
        df_filtered = df_filtered[df_filtered["Statut"] == selected_statut]

    # --- TABLEAU DE BORD (DASHBOARD) ---
    total_etablissements = len(df_filtered)
    total_ca = df_filtered["CA"].sum()
    
    # Calcul simplifié pour tes 3 statuts
    # (On compte le nombre de lignes pour chaque statut)
    nb_clients = len(df_filtered[df_filtered["Statut"].astype(str).str.contains("Client", case=False)])
    nb_discussion = len(df_filtered[df_filtered["Statut"].astype(str).str.contains("Discussion", case=False)])
    nb_prospects = len(df_filtered[df_filtered["Statut"].astype(str).str.contains("Prospect", case=False)])

    # Affichage des métriques
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    col1.metric("🏢 Total", total_etablissements)
    col2.metric("💰 CA Total", f"{total_ca:,.0f} €".replace(",", " "))
    col3.metric("✅ Clients", nb_clients)
    col4.metric("💬 Discussion", nb_discussion)
    col5.metric("🎯 Prospects", nb_prospects)
    st.markdown("---")

    # --- LA CARTE ---
    col_map, col_details = st.columns([2, 1])

    with col_map:
        st.subheader(f"Carte : {selected_region} > {selected_dept}")
        
        # Centrage
        if not df_filtered.empty and "Latitude" in df_filtered.columns:
            center_lat = df_filtered["Latitude"].mean()
            center_lon = df_filtered["Longitude"].mean()
            if selected_dept != "Tous":
                zoom = 10 
            elif selected_region != "Toutes":
                zoom = 8
            else:
                zoom = 6
        else:
            center_lat, center_lon, zoom = 46.6, 1.9, 6

        # Carte
        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles="CartoDB positron")

        # Ajout des POINTS avec les 3 COULEURS
        for index, row in df_filtered.iterrows():
            statut = str(row["Statut"]).lower()
            
            # --- LOGIQUE DES COULEURS ---
            if "client" in statut:
                color = "#2ecc71"  # VERT
                radius = 8
            elif "discussion" in statut:
                color = "#e67e22"  # ORANGE
                radius = 7
            elif "prospect" in statut:
                color = "#e74c3c"  # ROUGE
                radius = 5
            else:
                color = "#95a5a6"  # GRIS (si erreur de nom)
                radius = 5

            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=radius,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                popup=f"<b>{row['Nom Établissement']}</b><br>{row['Type']}<br>Statut: {row['Statut']}<br>CA: {row['CA']} €",
                tooltip=row["Nom Établissement"]
            ).add_to(m)

        st_folium(m, width="100%", height=600)

    # --- DÉTAILS ---
    with col_details:
        st.subheader("Détails chiffrés")
        if selected_region != "Toutes" and selected_dept == "Tous":
            st.write("📊 **CA par Département :**")
            ca_by_dept = df_filtered.groupby("Département")["CA"].sum().sort_values(ascending=False)
            st.dataframe(ca_by_dept)
        
        st.write("📋 **Liste :**")
        st.dataframe(
            df_filtered[["Nom Établissement", "Ville", "Statut", "CA"]], 
            hide_index=True,
            use_container_width=True
        )

else:
    st.warning("Aucune donnée chargée.")
