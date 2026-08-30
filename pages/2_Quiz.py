"""Page de passage d'un quiz (diagnostique avant/après, ou examen blanc chronométré)."""

import time

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from core import repository
from core.auth import exiger_identification
from core.db import init_db
from core.navigation import afficher_navigation
from core.quiz_service import corriger, message_resultat

st.set_page_config(
    page_title="Quiz", page_icon="assets/icone.png", layout="centered",
    initial_sidebar_state="expanded",
)
init_db()
afficher_navigation()

identifiant, prenom, api_key = exiger_identification()

quiz_id = st.session_state.get("quiz_id")
phase = st.session_state.get("phase")

if not quiz_id or not phase:
    st.warning(
        "Aucun quiz sélectionné pour l'instant.\n\n"
        "Cette page sert à **passer** un quiz déjà généré — pour en démarrer un : "
        "va dans **Mon cours**, ouvre l'onglet **Quiz**, génère-en un, puis clique "
        "sur son bouton « Passer le quiz »."
    )
    # Si un cours est déjà ouvert dans cette session, on y renvoie directement ;
    # sinon Mon cours afficherait à son tour "Aucun cours sélectionné" - autant
    # renvoyer tout de suite à l'accueil pour en choisir/créer un.
    if st.session_state.get("cours_id"):
        if st.button("Aller à Mon cours"):
            st.switch_page("pages/1_Mon_cours.py")
    else:
        if st.button("Aller à l'accueil"):
            st.switch_page("app.py")
    st.stop()

quiz_row = repository.obtenir_quiz(quiz_id)
if not quiz_row or not repository.obtenir_cours(quiz_row["cours_id"], identifiant):
    st.error("Ce quiz n'existe pas ou ne t'appartient pas.")
    if st.button("Retour à l'accueil"):
        st.switch_page("app.py")
    st.stop()

questions = repository.lister_questions(quiz_id)
noms_phase = {
    "avant": "Quiz diagnostique — avant révision",
    "apres": "Quiz diagnostique — après révision",
    "examen_blanc": "Examen blanc chronométré",
}
st.title(noms_phase.get(phase, "Quiz"))

# Réinitialise l'état si on démarre une nouvelle tentative (quiz ou phase différents)
session_key = f"{quiz_id}_{phase}"
if st.session_state.get("quiz_session_key") != session_key:
    st.session_state["quiz_session_key"] = session_key
    st.session_state["reponses"] = {i: None for i in range(len(questions))}
    st.session_state["quiz_debut"] = time.time()
    st.session_state["quiz_termine"] = False

est_examen = phase == "examen_blanc"
temps_ecoule = False

# --- Chrono (uniquement pour l'examen blanc) --------------------------------

if est_examen and not st.session_state.get("quiz_termine"):
    st_autorefresh(interval=1000, key="chrono_refresh")

if est_examen:
    from core.db import get_connection

    with get_connection() as conn:
        row = conn.execute("SELECT duree_minutes FROM quiz WHERE id = ?", (quiz_id,)).fetchone()
    duree_minutes = row["duree_minutes"] if row else 20
    duree_totale = duree_minutes * 60
    ecoule = time.time() - st.session_state["quiz_debut"]
    restant = max(0, int(duree_totale - ecoule))

    minutes, secondes = divmod(restant, 60)
    st.metric("Temps restant", f"{minutes:02d}:{secondes:02d}")
    if restant <= 60:
        st.caption("Moins d'une minute restante.")

    if restant <= 0:
        temps_ecoule = True
        st.session_state["quiz_termine"] = True

st.divider()

# --- Questions ---------------------------------------------------------------

reponses = st.session_state["reponses"]
quiz_verrouille = st.session_state.get("quiz_termine", False)

for i, q in enumerate(questions):
    st.markdown(f"**{i + 1}. {q['enonce']}**")
    choix_actuel = reponses.get(i)
    index_defaut = choix_actuel if choix_actuel is not None else None
    selection = st.radio(
        label=f"question_{i}",
        options=list(range(len(q["choix"]))),
        format_func=lambda idx, q=q: q["choix"][idx],
        index=index_defaut,
        key=f"radio_{quiz_id}_{phase}_{i}",
        label_visibility="collapsed",
        disabled=quiz_verrouille,
    )
    reponses[i] = selection
    st.write("")

st.session_state["reponses"] = reponses

# --- Validation ---------------------------------------------------------------

if not quiz_verrouille:
    if st.button("Valider mes réponses", type="primary"):
        st.session_state["quiz_termine"] = True
        st.rerun()

if temps_ecoule and not st.session_state.get("resultat_affiche"):
    st.warning("Temps écoulé. Ton examen a été soumis automatiquement.")

if st.session_state.get("quiz_termine"):
    liste_reponses = [reponses[i] for i in range(len(questions))]
    score, score_max = corriger(questions, liste_reponses)

    score_precedent = None
    if phase == "apres":
        tentative_avant = repository.derniere_tentative(quiz_id, "avant")
        if tentative_avant:
            score_precedent = tentative_avant["score"]

    if not st.session_state.get("resultat_sauve"):
        duree_secondes = int(time.time() - st.session_state["quiz_debut"])
        repository.sauver_tentative(quiz_id, phase, score, score_max, duree_secondes, liste_reponses)
        st.session_state["resultat_sauve"] = True

        # Petite célébration ponctuelle, une seule fois (pas à chaque rafraîchissement
        # de la page, ex: en ouvrant la correction détaillée juste en dessous) : soit
        # un sans-faute, soit une vraie progression par rapport à avant révision.
        if score_max and score == score_max:
            st.balloons()
        elif phase == "apres" and score_precedent is not None and score > score_precedent:
            st.balloons()

    st.divider()
    st.subheader(f"Résultat : {score} / {score_max}")
    pourcentage = round(100 * score / score_max) if score_max else 0
    st.progress(pourcentage / 100, text=f"{pourcentage}%")

    st.info(message_resultat(phase, score, score_max, score_precedent))

    def _retour_au_cours():
        for cle in ["quiz_session_key", "reponses", "quiz_debut", "quiz_termine", "resultat_sauve"]:
            st.session_state.pop(cle, None)
        st.switch_page("pages/1_Mon_cours.py")

    # Bouton dupliqué en haut ET en bas : sans ça, il faut faire défiler toutes les
    # explications de correction (jusqu'à 15 questions pour l'examen blanc) juste
    # pour quitter la page.
    if st.button("Retour au cours", key="retour_haut"):
        _retour_au_cours()

    with st.expander("Voir la correction détaillée, question par question"):
        for i, q in enumerate(questions):
            bonne = q["bonne_reponse_index"]
            donnee = liste_reponses[i]
            if donnee == bonne:
                st.success(f"**{i + 1}.** {q['enonce']}")
            else:
                reponse_donnee = q["choix"][donnee] if donnee is not None else "(pas de réponse)"
                st.error(f"**{i + 1}.** {q['enonce']}\n\nTa réponse : {reponse_donnee}\n\nBonne réponse : {q['choix'][bonne]}")
            if q.get("explication"):
                st.caption(q["explication"])

    if st.button("Retour au cours", key="retour_bas"):
        _retour_au_cours()
