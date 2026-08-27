"""Page de passage d'un quiz (diagnostique avant/après, ou examen blanc chronométré)."""

import time

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from core import repository
from core.auth import exiger_identification
from core.db import init_db
from core.quiz_service import corriger

st.set_page_config(page_title="Quiz", page_icon="📝", layout="centered")
init_db()

pseudo, api_key = exiger_identification()

quiz_id = st.session_state.get("quiz_id")
phase = st.session_state.get("phase")

if not quiz_id or not phase:
    st.warning("Aucun quiz sélectionné.")
    if st.button("← Retour"):
        st.switch_page("app.py")
    st.stop()

quiz_row = repository.obtenir_quiz(quiz_id)
if not quiz_row or not repository.obtenir_cours(quiz_row["cours_id"], pseudo):
    st.error("Ce quiz n'existe pas ou ne t'appartient pas.")
    if st.button("← Retour à l'accueil"):
        st.switch_page("app.py")
    st.stop()

questions = repository.lister_questions(quiz_id)
noms_phase = {
    "avant": "Quiz diagnostique — avant révision",
    "apres": "Quiz diagnostique — après révision",
    "examen_blanc": "Examen blanc chronométré",
}
st.title(f"📝 {noms_phase.get(phase, 'Quiz')}")

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
    couleur = "🟢" if restant > 60 else "🔴"
    st.metric(f"{couleur} Temps restant", f"{minutes:02d}:{secondes:02d}")

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
    if st.button("✅ Valider mes réponses", type="primary"):
        st.session_state["quiz_termine"] = True
        st.rerun()

if temps_ecoule and not st.session_state.get("resultat_affiche"):
    st.warning("⏰ Temps écoulé ! Ton examen a été soumis automatiquement.")

if st.session_state.get("quiz_termine"):
    liste_reponses = [reponses[i] for i in range(len(questions))]
    score, score_max = corriger(questions, liste_reponses)

    if not st.session_state.get("resultat_sauve"):
        duree_secondes = int(time.time() - st.session_state["quiz_debut"])
        repository.sauver_tentative(quiz_id, phase, score, score_max, duree_secondes, liste_reponses)
        st.session_state["resultat_sauve"] = True

    st.divider()
    st.subheader(f"Résultat : {score} / {score_max}")
    pourcentage = round(100 * score / score_max) if score_max else 0
    st.progress(pourcentage / 100, text=f"{pourcentage}%")

    for i, q in enumerate(questions):
        bonne = q["bonne_reponse_index"]
        donnee = liste_reponses[i]
        if donnee == bonne:
            st.success(f"**{i + 1}.** {q['enonce']} ✅")
        else:
            reponse_donnee = q["choix"][donnee] if donnee is not None else "(pas de réponse)"
            st.error(f"**{i + 1}.** {q['enonce']}\n\nTa réponse : {reponse_donnee}\n\nBonne réponse : {q['choix'][bonne]}")
        if q.get("explication"):
            st.caption(f"💡 {q['explication']}")

    if st.button("← Retour au cours"):
        for cle in ["quiz_session_key", "reponses", "quiz_debut", "quiz_termine", "resultat_sauve"]:
            st.session_state.pop(cle, None)
        st.switch_page("pages/1_Mon_cours.py")
