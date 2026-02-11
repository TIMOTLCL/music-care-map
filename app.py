import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import unicodedata

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(layout="wide", page_title="Music Care CRM", page_icon="🎵")

# --- TON LIEN GOOGLE SHEET ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS260Q3Tz1OIuDTZOu7ptoADnF26sjp3RLFOPYzylLZ77ZiP1KuA11-OzxNM6ktWkwL1qpylnWb1ZV4/pub?output=tsv"

# --- FONCTIONS UTILES ---
def remove_accents(input_str):
    if not isinstance(input_str, str): return str(input_str)
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

@st.cache_data(ttl=60)
def load_data():
    try:
        data = pd.read_csv(SHEET_URL, sep="\t")
        data.columns = data.columns.str.strip() 
        
        # Nettoyage CA
        if "CA" in data.columns:
            data["CA"] = data["CA"].astype(str).str.replace(",", ".").str.replace(r'[^\d.-]', '', regex=True)
            data["CA"] = pd.to_numeric(data["CA"], errors='coerce').fillna(0)

        # Statut Clean
        if "Statut" in data.columns:
            data["Statut_Clean"] = data["Statut"].apply(lambda x: remove_accents(str(x)).lower().strip())
        
        # Colonne Recherche
        if "Nom Établissement" in data.columns and "Ville" in data.columns:
            data["Recherche"] = data["Nom Établissement"] + " (" + data["Ville"] + ")"
        else:
            data["Recherche"] = data.index.astype(str)
            
        # Gestion Visite
        if "Visite prévue" not in data.columns:
            data["Visite prévue"] = "-"
        else:
            data["Visite prévue"] = data["Visite prévue"].fillna("-").astype(str)

        # Gestion Services
        if "Services" not in data.columns:
            data["Services"] = "-"
        else:
            data["Services"] = data["Services"].fillna("-").astype(str)
            
        return data
    except Exception as e:
        st.error(f"Erreur de lecture : {e}")
        return pd.DataFrame()

df = load_data()

# --- TITRE ---
st.title("🎵 Music Care - Pilotage Commercial")

if not df.empty and "Latitude" in df.columns:
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.header("🔍 Outils & Filtres")

        # RECHERCHE
        st.markdown("### ⚡ Recherche Rapide")
        search_options = ["-"] + sorted(list(df["Recherche"].unique()))
        search_target = st.selectbox("Trouver un établissement :", search_options)
        
        st.markdown("---")
        st.markdown("### 🌪️ Filtres")
        
        show_visits_only = st.checkbox("📅 Uniquement visites prévues")

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

        # 5. FILTRE SERVICES
        selected_services = []
        if "Services" in df.columns:
            unique_services = set()
            for items in df["Services"].dropna().astype(str):
                if items != "-":
                    for item in items.split(","):
                        unique_services.add(item.strip())
            
            services_options = sorted(list(unique_services))
            selected_services = st.multiselect("5. Services (Choix multiple)", services_options)

    # --- LOGIQUE FILTRE ---
    df_filtered = df.copy()
    
    if search_target != "-":
        df_filtered = df_filtered[df_filtered["Recherche"] == search_target]
        st.info(f"📍 Focus sur : **{search_target}**")
    else:
        if show_visits_only:
            df_filtered = df_filtered[df_filtered["Visite prévue"].str.len() > 1]
            if df_filtered.empty: st.warning("Aucune visite prévue trouvée.")

        if selected_region != "Toutes": df_filtered = df_filtered[df_filtered["Région"] == selected_region]
        if selected_dept != "Tous": df_filtered = df_filtered[df_filtered["Département"] == selected_dept]
        if selected_type != "Tous": df_filtered = df_filtered[df_filtered["Type"] == selected_type]
        if selected_statut != "Tous": df_filtered = df_filtered[df_filtered["Statut"] == selected_statut]
        
        if selected_services:
            mask = df_filtered["Services"].apply(lambda x: any(svc in str(x) for svc in selected_services))
            df_filtered = df_filtered[mask]

    # --- NOUVEAUX KPI (DASHBOARD FINANCIER) ---
    st.markdown("---")
    
    # Calculs des volumes
    total_etablissements = len(df_filtered)
    nb_clients = len(df_filtered[df_filtered["Statut_Clean"].str.contains("client", na=False)])
    nb_discussion = len(df_filtered[df_filtered["Statut_Clean"].str.contains("discussion", na=False)])
    nb_prospects = len(df_filtered[df_filtered["Statut_Clean"].str.contains("prospect", na=False)])

    # Calculs Financiers (L'intelligence métier)
    ca_total = df_filtered["CA"].sum()
    ca_clients = df_filtered[df_filtered["Statut_Clean"].str.contains("client", na=False)]["CA"].sum()
    ca_devis = df_filtered[df_filtered["Statut_Clean"].str.contains("discussion", na=False)]["CA"].sum()

    # Affichage Ligne 1 : Volumes
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🏢 Établissements (Filtre)", total_etablissements)
    col2.metric("✅ Clients Actifs", nb_clients)
    col3.metric("💬 En Discussion", nb_discussion)
    col4.metric("🎯 Prospects", nb_prospects)
    
    st.write("") # Petit espace
    
    # Affichage Ligne 2 : Finances
    colA, colB, colC = st.columns(3)
    colA.metric("💰 CA Total Affiché", f"{ca_total:,.0f} €".replace(",", " "))
    colB.metric("💶 CA Sécurisé (Clients)", f"{ca_clients:,.0f} €".replace(",", " "))
    colC.metric("⏳ Pipeline Devis (Discussions)", f"{ca_devis:,.0f} €".replace(",", " "))
    st.markdown("---")

    # --- CARTE ---
    col_map, col_details = st.columns([2, 1])

    with col_map:
        if not df_filtered.empty:
            center_lat = df_filtered["Latitude"].mean()
            center_lon = df_filtered["Longitude"].mean()
            if len(df_filtered) == 1: zoom = 15 
            elif selected_dept != "Tous": zoom = 10
            elif selected_region != "Toutes": zoom = 8
            else: zoom = 6
        else: center_lat, center_lon, zoom = 46.6, 1.8, 6

        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles="CartoDB positron")

        for index, row in df_filtered.iterrows():
            statut_clean = str(row.get("Statut_Clean", ""))
            
            if "client" in statut_clean: color, radius, z_idx = "#2ecc71", 6, 1000
            elif "discussion" in statut_clean: color, radius, z_idx = "#3498db", 5, 900
            elif "refuse" in statut_clean: color, radius, z_idx = "#9b59b6", 4, 100
            elif "resilie" in statut_clean: color, radius, z_idx = "#e74c3c", 5, 500
            elif "prospect" in statut_clean: color, radius, z_idx = "#95a5a6", 4, 100
            else: color, radius, z_idx = "#95a5a6", 4, 100

            lien_hubspot = str(row.get('Lien HubSpot', ''))
            bouton_html = ""
            if "http" in lien_hubspot and str(lien_hubspot) != "nan":
                bouton_html = f"""
                <br>
                <a href="{lien_hubspot}" target="_blank" style="display: inline-block; background-color: #ff7a59; color: white; padding: 6px 10px; text-decoration: none; border-radius: 4px; font-size: 11px; margin-top: 5px;">🟠 HubSpot</a>
                """

            visite_info = str(row.get('Visite prévue', '-'))
            visite_html = ""
            if len(visite_info) > 1 and visite_info != "nan":
                visite_html = f"<br>📅 <b>Visite : {visite_info}</b>"

            services_info = str(row.get('Services', '-'))
            services_html = ""
            if len(services_info) > 1 and services_info != "nan" and services_info != "-":
                services_html = f"🏥 Services: <i>{services_info}</i><br>"

            nom = row.get('Nom Établissement', 'Inconnu')
            statut_officiel = row.get('Statut', '-')
            type_etab = row.get('Type', '-')
            ca = row.get('CA', 0)
            
            # Petit ajustement d'affichage selon si c'est un client ou un devis
            label_ca = "CA" if "client" in statut_clean else "Devis" if "discussion" in statut_clean else "Montant"

            popup_content = f"""
            <div style="font-family: sans-serif; width: 220px;">
                <b>{nom}</b><br>
                <i style="color:gray;">{type_etab}</i><br>
                <hr style="margin: 5px 0;">
                Statut: <b>{statut_officiel}</b><br>
                {services_html}
                {label_ca}: {ca} €
                {visite_html}
                {bouton_html}
            </div>
            """

            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=radius, color=color, weight=1, fill=True, fill_color=color, fill_opacity=0.8,
                popup=folium.Popup(popup_content, max_width=250),
                tooltip=nom, z_index_offset=z_idx 
            ).add_to(m)

        st_folium(m, width="100%", height=600)

    # --- DÉTAILS ---
    with col_details:
        st.subheader("Détails")
        if selected_region != "Toutes" and selected_dept == "Tous":
            st.caption("CA par Département")
            ca_by_dept = df_filtered.groupby("Département")["CA"].sum().sort_values(ascending=False)
            st.dataframe(ca_by_dept, use_container_width=True)
        
        cols_display = ["Nom Établissement", "Ville", "Statut", "Services", "CA", "Lien HubSpot", "Visite prévue"]
        cols_final = [c for c in cols_display if c in df_filtered.columns]

        st.dataframe(
            df_filtered, 
            column_config={
                "Lien HubSpot": st.column_config.LinkColumn("Lien CRM", display_text="Ouvrir")
            },
            column_order=cols_final,
            hide_index=True,
            use_container_width=True
        )

else:
    st.warning("⚠️ Données non chargées.")
