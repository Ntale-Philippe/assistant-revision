"""Entraînement : questions à réponse écrite (rédigées, pas à choix multiples),
corrigées par l'IA. Un mode d'entraînement séparé des 3 quiz habituels — ne compte
pas dans le suivi de progression avant/après."""

import streamlit as st

from core import repository
from core.auth import exiger_identification
from core.db import init_db
from core.mistral_client import message_utilisateur
from core.navigation import afficher_navigation
from core.quiz_service import corriger_ecrit

st.set_page_config(page_title="Questions à réponse écrite", page_icon="assets/icone.png", layout="centered")
init_db()
afficher_navigation()

identifiant, prenom, api_key = exiger_identification()

quiz_id = st.session_state.get("quiz_ecrit_id")
if not quiz_id:
    st.warning("Aucune session de questions écrites sélectionnée.")
    if st.button("Retour à l'accueil"):
        st.switch_page("app.py")
    st.stop()

quiz_row = repository.obtenir_quiz(quiz_id)
if not quiz_row or not repository.obtenir_cours(quiz_row["cours_id"], identifiant):
    st.error("Ce quiz n'existe pas ou ne t'appartient pas.")
    if st.button("Retour à l'accueil"):
        st.switch_page("app.py")
    st.stop()

questions = repository.lister_questions(quiz_id)

st.title("Questions à réponse écrite")
st.caption(
    "Rédige tes réponses avec tes propres mots — l'IA compare au contenu attendu, "
    "pas mot pour mot. Entraînement libre, sans chrono."
)

# Réinitialise l'état si on démarre une nouvelle tentative sur ce jeu de questions.
session_key = f"ecrit_{quiz_id}"
if st.session_state.get("ecrit_session_key") != session_key:
    st.session_state["ecrit_session_key"] = session_key
    st.session_state["ecrit_reponses"] = {i: "" for i in range(len(questions))}
    st.session_state["ecrit_termine"] = False
    st.session_state.pop("ecrit_resultat", None)

st.divider()

termine = st.session_state.get("ecrit_termine", False)

for i, q in enumerate(questions):
    st.markdown(f"**{i + 1}. {q['enonce']}**")
    reponse = st.text_area(
        label=f"reponse_{i}",
        value=st.session_state["ecrit_reponses"].get(i, ""),
        key=f"textarea_{quiz_id}_{i}",
        label_visibility="collapsed",
        disabled=termine,
        height=100,
        placeholder="Rédige ta réponse ici...",
    )
    st.session_state["ecrit_reponses"][i] = reponse
    st.write("")

if not termine:
    if st.button("Valider mes réponses", type="primary"):
        reponses_texte = [st.session_state["ecrit_reponses"][i] for i in range(len(questions))]
        with st.spinner("L'IA corrige tes réponses..."):
            try:
                score, score_max, details = corriger_ecrit(questions, reponses_texte)
                st.session_state["ecrit_resultat"] = {
                    "score": score,
                    "score_max": score_max,
                    "details": details,
                    "reponses": reponses_texte,
                }
                st.session_state["ecrit_termine"] = True
                repository.sauver_tentative(quiz_id, "ecrit", score, score_max, None, reponses_texte, details)
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {message_utilisateur(e)}")

if termine and st.session_state.get("ecrit_resultat"):
    resultat = st.session_state["ecrit_resultat"]
    st.divider()
    st.subheader(f"Résultat : {resultat['score']} / {resultat['score_max']}")
    pourcentage = round(100 * resultat["score"] / resultat["score_max"]) if resultat["score_max"] else 0
    st.progress(pourcentage / 100, text=f"{pourcentage}%")

    for i, q in enumerate(questions):
        detail = resultat["details"][i] if i < len(resultat["details"]) else {}
        st.markdown(f"**{i + 1}. {q['enonce']}**")
        if detail.get("correcte"):
            st.success(f"Ta réponse : {resultat['reponses'][i] or '(pas de réponse)'}")
        else:
            st.error(f"Ta réponse : {resultat['reponses'][i] or '(pas de réponse)'}")
        if detail.get("commentaire"):
            st.caption(detail["commentaire"])
        with st.expander("Réponse modèle"):
            st.write(q["reponse_modele"])

    if st.button("Retour au cours"):
        for cle in ["ecrit_session_key", "ecrit_reponses", "ecrit_termine", "ecrit_resultat"]:
            st.session_state.pop(cle, None)
        st.switch_page("pages/1_Mon_cours.py")
