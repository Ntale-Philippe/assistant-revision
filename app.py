"""Page d'accueil : identification, liste des cours, création d'un nouveau cours."""

import streamlit as st

from core import repository
from core.auth import PROPRIETAIRE_SOLO, exiger_identification, lien_personnel
from core.db import init_db

st.set_page_config(page_title="Mon assistant de révision", page_icon="🧬", layout="centered")

init_db()

pseudo, api_key = exiger_identification()

st.title("🧬 Mon assistant de révision")
st.caption("Dépose tes notes, génère une synthèse et teste-toi avec des quiz.")

if pseudo != PROPRIETAIRE_SOLO:
    # Mode partagé : plusieurs personnes utilisent la même appli, chacune avec son espace.
    col1, col2 = st.columns([4, 1])
    with col1:
        st.info(f"👋 Connecté en tant que **{pseudo}**. Tes cours sont privés, personne d'autre ne les voit.")
    with col2:
        if st.button("Changer de personne"):
            st.query_params.clear()
            st.rerun()

    with st.expander("🔖 Mon lien personnel (à mettre en favori sur ton téléphone)"):
        st.write(
            "Ajoute ce lien à l'écran d'accueil de ton téléphone pour retrouver "
            "directement ton espace, sans avoir à retaper ton prénom et ta clé :"
        )
        st.code(lien_personnel(pseudo, api_key), language=None)
        st.caption("⚠️ Ne partage jamais CE lien précis : il contient ta clé API personnelle.")

st.divider()

# --- Formulaire de création d'un cours --------------------------------------

with st.expander("➕ Nouveau cours", expanded=False):
    with st.form("nouveau_cours_form", clear_on_submit=True):
        nom = st.text_input("Nom du cours", placeholder="Ex : Biochimie métabolique")
        description = st.text_area("Description (optionnel)", placeholder="Quelques mots sur le cours...")
        submitted = st.form_submit_button("Créer le cours")
        if submitted:
            if nom.strip():
                repository.creer_cours(pseudo, nom.strip(), description.strip())
                st.success(f"Cours « {nom} » créé !")
                st.rerun()
            else:
                st.error("Le nom du cours est obligatoire.")

st.divider()

# --- Liste des cours ----------------------------------------------------------

cours_list = repository.lister_cours(pseudo)

if not cours_list:
    st.info("Aucun cours pour l'instant. Crée ton premier cours ci-dessus ! 👆")
else:
    st.subheader("Mes cours")
    for cours in cours_list:
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"### {cours['nom']}")
                if cours.get("description"):
                    st.caption(cours["description"])
            with col2:
                if st.button("Ouvrir →", key=f"ouvrir_{cours['id']}"):
                    st.session_state["cours_id"] = cours["id"]
                    st.switch_page("pages/1_Mon_cours.py")
