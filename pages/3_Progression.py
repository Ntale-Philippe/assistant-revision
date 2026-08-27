"""Page de progression : score avant/après, historique des examens blancs."""

import pandas as pd
import streamlit as st

from core import repository
from core.auth import exiger_identification
from core.db import init_db

st.set_page_config(page_title="Progression", layout="centered")
init_db()

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
