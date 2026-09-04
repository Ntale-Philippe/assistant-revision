"""Examen écrit chronométré : questions à réponse écrite (rédigées, pas à choix
multiples), corrigées par l'IA. Un 4ᵉ mode séparé des 3 quiz habituels — ne compte
pas dans le suivi de progression avant/après."""

import time

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from core import repository
from core.auth import exiger_identification
from core.db import init_db
from core.mistral_client import message_utilisateur
from core.navigation import afficher_navigation
from core.quiz_service import corriger_ecrit, message_resultat

st.set_page_config(
    page_title="Examen écrit", page_icon="assets/icone.png", layout="centered",
    initial_sidebar_state="expanded",
)
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

st.title("Examen écrit chronométré")
st.caption(
    "Rédige tes réponses avec tes propres mots — l'IA compare au contenu attendu, "
    "pas mot pour mot."
)

# Réinitialise l'état si on démarre une nouvelle tentative sur ce jeu de questions.
session_key = f"ecrit_{quiz_id}"
if st.session_state.get("ecrit_session_key") != session_key:
    st.session_state["ecrit_session_key"] = session_key
    st.session_state["ecrit_reponses"] = {i: "" for i in range(len(questions))}
    st.session_state["ecrit_termine"] = False
    st.session_state["ecrit_debut"] = time.time()
    st.session_state.pop("ecrit_resultat", None)
    st.session_state["ecrit_details_partiel"] = {}

termine = st.session_state.get("ecrit_termine", False)
temps_ecoule = False

# --- Chrono --------------------------------------------------------------------

if not termine:
    st_autorefresh(interval=1000, key="chrono_ecrit_refresh")

duree_minutes = quiz_row.get("duree_minutes") or 15
duree_totale = duree_minutes * 60
ecoule = time.time() - st.session_state["ecrit_debut"]
restant = max(0, int(duree_totale - ecoule))

if not termine:
    minutes, secondes = divmod(restant, 60)
    st.metric("Temps restant", f"{minutes:02d}:{secondes:02d}")
    if restant <= 60:
        st.caption("Moins d'une minute restante.")
    if restant <= 0:
        temps_ecoule = True

st.divider()

def _corriger_manquants(indices: list[int]):
    """Corrige (IA) les questions de `indices` dont le texte actuel n'est pas déjà
    en cache - appelée question par question dès que l'étudiant quitte un champ,
    ET en rattrapage sur toutes les questions au moment de valider. Comme la plupart
    sont déjà corrigées au fil de l'examen, il ne reste presque jamais rien à
    corriger à ce moment-là : le résultat s'affiche donc immédiatement, sans le
    délai d'un gros appel IA final. Une réponse vidée après coup oublie sa
    correction (sinon elle resterait comptée comme bonne alors qu'elle est vide)."""
    cache = st.session_state.setdefault("ecrit_details_partiel", {})
    a_faire = []
    for i in indices:
        texte = (st.session_state["ecrit_reponses"].get(i) or "").strip()
        if not texte:
            cache.pop(i, None)
            continue
        if cache.get(i, {}).get("texte") == texte:
            continue  # déjà corrigé pour ce texte exact
        a_faire.append(i)
    if not a_faire:
        return
    sous_reponses = [(st.session_state["ecrit_reponses"][i] or "").strip() for i in a_faire]
    _, _, sous_details = corriger_ecrit([questions[i] for i in a_faire], sous_reponses)
    for idx, i in enumerate(a_faire):
        cache[i] = {"texte": sous_reponses[idx], **sous_details[idx]}


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
    if not termine and reponse.strip():
        try:
            _corriger_manquants([i])
        except Exception:
            pass  # pas grave : rattrapé automatiquement à la validation
    st.write("")


def _corriger_et_sauver():
    # Rattrape toute question pas encore corrigée (ex: modifiée juste avant de
    # valider, sans avoir quitté le champ) - normalement peu ou rien à ce stade.
    _corriger_manquants(list(range(len(questions))))
    cache = st.session_state.get("ecrit_details_partiel", {})

    reponses_texte = [st.session_state["ecrit_reponses"][i] for i in range(len(questions))]
    # `cache[i]` contient aussi la clé "texte" (interne, sert juste à savoir si une
    # réponse a déjà été corrigée) - on ne garde que correcte/commentaire, comme avant.
    details = [
        {"correcte": cache[i]["correcte"], "commentaire": cache[i]["commentaire"]}
        if i in cache
        else {"correcte": False, "commentaire": "Pas de réponse donnée."}
        for i in range(len(questions))
    ]
    score = sum(1 for d in details if d.get("correcte"))
    score_max = len(questions)

    st.session_state["ecrit_resultat"] = {
        "score": score,
        "score_max": score_max,
        "details": details,
        "reponses": reponses_texte,
    }
    st.session_state["ecrit_termine"] = True
    duree_secondes = int(time.time() - st.session_state["ecrit_debut"])
    repository.sauver_tentative(quiz_id, "ecrit", score, score_max, duree_secondes, reponses_texte, details)
    # Cette fonction n'est appelée qu'une fois par soumission (jamais au réaffichage
    # du résultat) : pas de risque de répéter la célébration à chaque interaction.
    if score_max and score == score_max:
        st.session_state["ecrit_celebrer"] = True


if not termine:
    if temps_ecoule:
        st.warning("Temps écoulé. Ton examen est en cours de correction...")
        with st.spinner("L'IA corrige tes réponses..."):
            try:
                _corriger_et_sauver()
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {message_utilisateur(e)}")
    elif st.button("Valider mes réponses", type="primary"):
        with st.spinner("L'IA corrige tes réponses..."):
            try:
                _corriger_et_sauver()
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {message_utilisateur(e)}")

if termine and st.session_state.get("ecrit_resultat"):
    resultat = st.session_state["ecrit_resultat"]
    if st.session_state.pop("ecrit_celebrer", False):
        st.balloons()
    st.divider()
    st.subheader(f"Résultat : {resultat['score']} / {resultat['score_max']}")
    pourcentage = round(100 * resultat["score"] / resultat["score_max"]) if resultat["score_max"] else 0
    st.progress(pourcentage / 100, text=f"{pourcentage}%")
    st.info(message_resultat("ecrit", resultat["score"], resultat["score_max"]))

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
        for cle in [
            "ecrit_session_key", "ecrit_reponses", "ecrit_termine", "ecrit_debut",
            "ecrit_resultat", "ecrit_details_partiel",
        ]:
            st.session_state.pop(cle, None)
        st.switch_page("pages/1_Mon_cours.py")
