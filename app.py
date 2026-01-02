import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(layout="wide", page_title="Music Care CRM")

# --- TON LIEN GOOGLE SHEET ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS260Q3Tz1OIuDTZOu7ptoADnF26sjp3RLFOPYzylLZ77ZiP1KuA11-OzxNM6ktWkwL1qpylnWb1ZV4/pub?output=tsv"

# --- FONCTION DE CHARGEMENT ---
@st.cache_data(ttl=300)
def load_data():
    try:
        data = pd.read_csv(SHEET_URL, sep="\t")
        
        # 1. NETTOYAGE DES TITRES DE COLONNES (Enlève les espaces invisibles)
        # Transforme "Statut " en "Statut"
        data.columns = data.columns.str.strip()
        
        # 2. Nettoyage du CA
        if "CA" in data.columns:
            data["CA"] = data["CA"].astype(str)
            data["CA"] = data["CA"].str.replace(",", ".")
            data["CA"] = data["CA"].str.replace(r'[^\d.-]', '', regex=True)
            data["CA"] = pd.to_numeric(data["CA"], errors='coerce').fillna(0)
            
        return data
    except Exception as e:
        st.error(f"Erreur de lecture du fichier : {e}")
        return pd.DataFrame()

df = load_data()

# --- TITRE ---
st.title("📊 Music Care - Pilotage Commercial")

if not df.empty and "Latitude" in df.columns:
    
    # --- DEBUG : AFFICHER CE QUE L'ORDI VOIT ---
    # Cela va t'aider à comprendre pourquoi une couleur ne s'affiche pas
    with st.sidebar:
        st.header("🔍 Filtres")
        
        # Section Debug pour vérifier les Statuts
        with st.expander("🕵️ DEBUG : Vérifier mes Statuts"):
            if "Statut" in df.columns:
                st.write("Voici les statuts exacts trouvés dans ton fichier :")
                st.write(df["Statut"].unique())
            else:
                st.error("Colonne 'Statut' introuvable ! Vérifie l'orthographe (Majuscule ?).")
                st.write("Colonnes trouvées :", df.columns.tolist())

        # 1. Région
        if "Région" in df.columns:
            region_list = ["Toutes"] + sorted(list(df["Région"].dropna().unique()))
            selected_region = st.selectbox("1. Région", region_list)
        else:
            selected_region = "Toutes"
        
        # 2. Département
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

    # --- FILTRAGE ---
    df_filtered = df.copy()
    
    if selected_region != "Toutes":
        df_filtered = df_filtered[df_filtered["Région"] == selected_region]
    if selected_dept != "Tous":
        df_filtered = df_filtered[df_filtered["Département"] == selected_dept]
    if selected_type != "Tous":
        df_filtered = df_filtered[df_filtered["Type"] == selected_type]
    if selected_statut != "Tous":
        df_filtered = df_filtered[df_filtered["Statut"] == selected_statut]

    # --- KPI ---
    total_etablissements = len(df_filtered)
    total_ca = df_filtered["CA"].sum()
    
    # Calculs KPI sécurisés
    if "Statut" in df_filtered.columns:
        nb_clients = len(df_filtered[df_filtered["Statut"].astype(str).str.contains("Client", case=False, na=False)])
        nb_prospects = len(df_filtered[df_filtered["Statut"].astype(str).str.contains("Prospect", case=False, na=False)])
    else:
        nb_clients = 0
        nb_prospects = 0

    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🏢 Total affiché", total_etablissements)
    col2.metric("💰 CA Total", f"{total_ca:,.0f} €".replace(",", " "))
    col3.metric("✅ Clients", nb_clients)
    col4.metric("🎯 Prospects", nb_prospects)
    st.markdown("---")

    # --- CARTE ---
    col_map, col_details = st.columns([2, 1])

    with col_map:
        st.subheader(f"Carte : {selected_region}")
        
        # Centrage
        if not df_filtered.empty:
            center_lat = df_filtered["Latitude"].mean()
            center_lon = df_filtered["Longitude"].mean()
            zoom = 6
            if selected_dept != "Tous": zoom = 10
            elif selected_region != "Toutes": zoom = 8
        else:
            center_lat, center_lon, zoom = 46.6, 1.8, 6

        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles="CartoDB positron")
        marker_cluster = MarkerCluster().add_to(m)

        for index, row in df_filtered.iterrows():
            # On récupère le statut, on enlève les espaces autour, et on met en minuscule
            statut_brut = str(row.get("Statut", "")).strip()
            statut = statut_brut.lower()
            
            # --- LOGIQUE COULEURS STRICTE ---
            if "client" in statut:
                color = "#2ecc71"  # VERT (Client)
            elif "discussion" in statut:
                color = "#3498db"  # BLEU (Discussion)
            elif "refusé" in statut or "refuse" in statut:
                color = "#9b59b6"  # VIOLET (Refusé)
            elif "resilie" in statut or "résilié" in statut:
                color = "#e74c3c"  # ROUGE (Résilié)
            elif "prospect" in statut:
                color = "#95a5a6"  # GRIS (Prospect)
            else:
                color = "#95a5a6"  # GRIS par défaut (Si ça ne matche rien)

            # Contenu de la bulle info
            nom = row.get('Nom Établissement', 'Inconnu')
            type_etab = row.get('Type', '-')
            ca = row.get('CA', 0)

            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=7,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.9,
                popup=f"<b>{nom}</b><br>{type_etab}<br>Statut: {statut_brut}<br>CA: {ca} €",
                tooltip=nom
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
        cols_to_show = ["Nom Établissement", "Ville", "Statut", "CA"]
        # On ne garde que les colonnes qui existent vraiment
        cols_existantes = [c for c in cols_to_show if c in df_filtered.columns]
        
        st.dataframe(
            df_filtered[cols_existantes], 
            hide_index=True,
            use_container_width=True
        )

else:
    st.warning("⚠️ Données non chargées. Regarde l'erreur ci-dessus.")
