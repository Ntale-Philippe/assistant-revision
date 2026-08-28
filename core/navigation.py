"""Menu de navigation affiché manuellement dans chaque page.

Le menu automatique de Streamlit est désactivé (voir .streamlit/config.toml)
pour ne pas afficher "Administration" à tous les visiteurs — cette page reste
accessible directement par son adresse (réservée au vendeur, protégée par mot
de passe), mais n'apparaît dans aucun menu visible par les clients.
"""

import streamlit as st


def afficher_navigation():
    with st.sidebar:
        st.page_link("app.py", label="Accueil")
        st.page_link("pages/1_Mon_cours.py", label="Mon cours")
        st.page_link("pages/2_Quiz.py", label="Quiz")
        st.page_link("pages/3_Progression.py", label="Progression")
        st.page_link("pages/5_Conditions.py", label="Conditions d'utilisation")
