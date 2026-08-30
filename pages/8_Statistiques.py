"""Page de statistiques : chiffres personnels et globaux, visibles par tout le
monde. Les insights avancés réservés au propriétaire sont dans une page séparée
(pages/9_Statistiques_avancees.py), volontairement absente du menu de navigation
pour que les étudiants n'en voient même pas l'existence."""

import streamlit as st

from core import repository
from core.auth import exiger_identification
from core.db import init_db
from core.navigation import afficher_navigation

st.set_page_config(
    page_title="Statistiques", page_icon="assets/icone.png", layout="centered",
    initial_sidebar_state="expanded",
)
init_db()
afficher_navigation()

identifiant, prenom, api_key = exiger_identification()

if st.button("Retour à l'accueil"):
    st.switch_page("app.py")

st.title("Statistiques")

# --- Mes statistiques ---------------------------------------------------------

st.subheader("Mes statistiques")
mes_stats = repository.statistiques_utilisateur(identifiant)

col1, col2, col3 = st.columns(3)
col1.metric("Mes cours", mes_stats["nb_cours"])
col2.metric("Documents déposés", mes_stats["nb_documents"])
col3.metric("Synthèses générées", mes_stats["nb_syntheses"])

col4, col5 = st.columns(2)
col4.metric("Quiz passés", mes_stats["nb_tentatives"])
col5.metric(
    "Mon score moyen",
    f"{mes_stats['score_moyen_pourcentage']}%" if mes_stats["score_moyen_pourcentage"] is not None else "—",
)

st.divider()

# --- Statistiques globales de l'appli ------------------------------------------

st.subheader("L'appli en chiffres")
st.caption("Tous les étudiants confondus (ton usage personnel n'est jamais visible des autres — ceci reste des totaux anonymes).")
globales = repository.statistiques_globales()

col1, col2, col3 = st.columns(3)
col1.metric("Étudiants inscrits", globales["nb_inscrits"])
col2.metric("Cours créés", globales["nb_cours"])
col3.metric("Documents déposés", globales["nb_documents"])

col4, col5, col6 = st.columns(3)
col4.metric("Synthèses générées", globales["nb_syntheses"])
col5.metric("Quiz passés", globales["nb_tentatives"])
col6.metric(
    "Score moyen (tous)",
    f"{globales['score_moyen_pourcentage']}%" if globales["score_moyen_pourcentage"] is not None else "—",
)

st.metric("Pays représentés", globales["nb_pays_representes"])
st.caption(
    "Basé sur les pays renseignés dans « Personnalise l'appli » sur l'accueil — "
    "pas de détail par pays ici, juste le nombre total."
)
