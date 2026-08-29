"""Page de progression : score avant/après, historique des tentatives, et revue
détaillée question par question de n'importe quelle tentative passée (utile pour
relire ses erreurs juste avant un examen)."""

import pandas as pd
import streamlit as st

from core import repository
from core.auth import exiger_identification
from core.db import init_db
from core.navigation import afficher_navigation

st.set_page_config(page_title="Progression", page_icon="assets/icone.png", layout="centered")
init_db()
afficher_navigation()

identifiant, prenom, api_key = exiger_identification()

if st.button("Retour à l'accueil"):
    st.switch_page("app.py")

st.title("Ma progression")

cours_list = repository.lister_cours(identifiant)
if not cours_list:
    st.info("Aucun cours pour l'instant.")
    st.stop()

cours_id_defaut = st.session_state.get("cours_id_progression") or st.session_state.get("cours_id")
noms = [c["nom"] for c in cours_list]
ids = [c["id"] for c in cours_list]
index_defaut = ids.index(cours_id_defaut) if cours_id_defaut in ids else 0

nom_choisi = st.selectbox("Choisis un cours", noms, index=index_defaut)
cours_id = ids[noms.index(nom_choisi)]


def _afficher_revue(tentative: dict):
    """Détail question par question d'une tentative passée : ce qui a été
    répondu, ce qui était correct, et l'explication — comme juste après avoir
    passé le quiz, mais consultable n'importe quand après coup."""
    for i, q in enumerate(tentative["questions"]):
        st.markdown(f"**{i + 1}. {q['enonce']}**")
        if q.get("type_question") == "ecrite":
            detail = tentative["details"][i] if tentative["details"] and i < len(tentative["details"]) else {}
            reponse_donnee = tentative["reponses"][i] if i < len(tentative["reponses"]) else None
            texte_reponse = f"Ta réponse : {reponse_donnee or '(pas de réponse)'}"
            if detail.get("correcte"):
                st.success(texte_reponse)
            else:
                st.error(texte_reponse)
            if detail.get("commentaire"):
                st.caption(detail["commentaire"])
            with st.expander("Réponse modèle"):
                st.write(q.get("reponse_modele", ""))
        else:
            bonne = q["bonne_reponse_index"]
            donnee = tentative["reponses"][i] if i < len(tentative["reponses"]) else None
            if donnee == bonne:
                st.success(f"Ta réponse : {q['choix'][donnee]}")
            else:
                reponse_donnee = q["choix"][donnee] if donnee is not None else "(pas de réponse)"
                st.error(f"Ta réponse : {reponse_donnee}\n\nBonne réponse : {q['choix'][bonne]}")
            if q.get("explication"):
                st.caption(q["explication"])
        st.write("")


def _section_historique(titre: str, type_quiz: str, cle: str) -> bool:
    """Sélecteur de tentative passée + bouton pour en revoir le détail complet.
    Fonctionne même après avoir régénéré le quiz plusieurs fois : chaque
    régénération crée une nouvelle version, mais les anciennes tentatives restent
    consultables ici (voir repository.historique_tentatives). Retourne False si
    rien à afficher, pour que l'appelant puisse montrer un message à la place."""
    historique = repository.historique_tentatives(cours_id, type_quiz)
    if not historique:
        return False
    st.markdown(f"**{titre}**")
    options = [f"{t['created_at']} — {t['score']}/{t['score_max']}" for t in historique]
    choix = st.selectbox("Choisis une tentative à revoir", options, key=f"select_{cle}")
    tentative_choisie = historique[options.index(choix)]
    with st.expander("Voir le détail question par question", expanded=False):
        _afficher_revue(tentative_choisie)
    return True


st.divider()

# --- Progression avant / après (quiz diagnostique) --------------------------

quiz_diag = repository.obtenir_quiz_par_type(cours_id, "diagnostique")

st.subheader("Progression sur le quiz diagnostique")

if not quiz_diag:
    st.info("Pas encore de quiz diagnostique pour ce cours.")
else:
    tentative_avant = repository.derniere_tentative(quiz_diag["id"], "avant")
    tentative_apres = repository.derniere_tentative(quiz_diag["id"], "apres")

    if not tentative_avant:
        st.info("Passe d'abord le quiz « avant révision » depuis la page du cours.")
    else:
        donnees = {"Avant révision": tentative_avant["score"] / tentative_avant["score_max"] * 100}
        if tentative_apres:
            donnees["Après révision"] = tentative_apres["score"] / tentative_apres["score_max"] * 100

        df = pd.DataFrame({"Phase": list(donnees.keys()), "Score (%)": list(donnees.values())})
        st.bar_chart(df.set_index("Phase"))

        col1, col2 = st.columns(2)
        col1.metric("Avant révision", f"{tentative_avant['score']} / {tentative_avant['score_max']}")
        if tentative_apres:
            delta = tentative_apres["score"] - tentative_avant["score"]
            col2.metric(
                "Après révision",
                f"{tentative_apres['score']} / {tentative_apres['score_max']}",
                delta=delta,
            )
        else:
            col2.info("Pas encore repassé après révision.")

    st.write("")
    _section_historique("Revoir mes réponses (quiz diagnostique)", "diagnostique", "diag")

st.divider()

# --- Historique de l'examen blanc --------------------------------------------

st.subheader("Historique de l'examen blanc")

quiz_examen = repository.obtenir_quiz_par_type(cours_id, "examen_blanc")

if not quiz_examen:
    st.info("Pas encore d'examen blanc pour ce cours.")
else:
    tentatives = repository.lister_tentatives(quiz_examen["id"])
    if not tentatives:
        st.info("Pas encore passé l'examen blanc.")
    else:
        df = pd.DataFrame(
            {
                "Tentative": [f"#{i + 1}" for i in range(len(tentatives))],
                "Score (%)": [t["score"] / t["score_max"] * 100 for t in tentatives],
            }
        )
        st.line_chart(df.set_index("Tentative"))
        derniere = tentatives[-1]
        st.metric("Dernier score", f"{derniere['score']} / {derniere['score_max']}")

    st.write("")
    _section_historique("Revoir mes réponses (examen blanc)", "examen_blanc", "examen")

st.divider()

# --- Historique de l'examen écrit --------------------------------------------

st.subheader("Historique de l'examen écrit")
if not _section_historique("Revoir mes réponses (examen écrit)", "reponse_ecrite", "ecrit"):
    st.info("Pas encore passé l'examen écrit.")
