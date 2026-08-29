"""Page de démonstration publique : aucune inscription requise.

Montre un vrai exemple (synthèse + quiz) généré par l'appli sur un cours de
macroéconomie, pour qu'un visiteur comprenne la valeur en quelques secondes avant
même de créer son espace personnel.
"""

import streamlit as st

from core import repository
from core.config import IDENTIFIANT_DEMO
from core.db import init_db
from core.navigation import afficher_navigation
from core.quiz_service import corriger

st.set_page_config(page_title="Démo", page_icon="assets/icone.png", layout="centered")
init_db()
afficher_navigation()

st.title("Exemple concret, sans rien remplir")
st.write(
    "Voici un vrai résultat généré par cette appli à partir d'un cours de "
    "macroéconomie — pour te donner une idée avant de créer ton propre accès "
    "gratuit."
)

cours_demo_liste = repository.lister_cours(IDENTIFIANT_DEMO)
if not cours_demo_liste:
    st.info("La démonstration n'est pas encore prête, reviens un peu plus tard.")
    st.stop()

cours_demo = cours_demo_liste[0]
st.subheader(cours_demo["nom"])
if cours_demo.get("description"):
    st.caption(cours_demo["description"])

tab_synthese, tab_quiz = st.tabs(["Synthèse", "Quiz"])

with tab_synthese:
    synthese = repository.derniere_synthese(cours_demo["id"])
    if not synthese:
        st.info("Synthèse pas encore disponible.")
    else:
        with st.expander("Synthèse du cours", expanded=True):
            st.markdown(synthese["synthese_md"])
        with st.expander("Pourquoi ce sujet est important"):
            st.markdown(synthese["contexte_md"])
        with st.expander("Notions probables à l'examen"):
            st.markdown(synthese["notions_examen_md"])
        with st.expander("À retenir pour la vie"):
            st.caption("💫 Des faits et petites histoires intéressants à connaître, au-delà de l'examen.")
            st.markdown(synthese["a_retenir_md"])
        with st.expander("Anecdotes"):
            st.markdown(synthese["fun_facts_md"])

with tab_quiz:
    quiz_demo = repository.obtenir_quiz_par_type(cours_demo["id"], "diagnostique")
    if not quiz_demo:
        st.info("Quiz pas encore disponible.")
    else:
        questions = repository.lister_questions(quiz_demo["id"])
        st.caption(f"{len(questions)} questions — essaie-le pour de vrai, c'est gratuit et sans inscription.")

        reponses_demo = st.session_state.setdefault("demo_reponses", {})
        termine_demo = st.session_state.get("demo_termine", False)

        for i, q in enumerate(questions):
            st.markdown(f"**{i + 1}. {q['enonce']}**")
            selection = st.radio(
                label=f"demo_question_{i}",
                options=list(range(len(q["choix"]))),
                format_func=lambda idx, q=q: q["choix"][idx],
                index=reponses_demo.get(i),
                key=f"demo_radio_{i}",
                label_visibility="collapsed",
                disabled=termine_demo,
            )
            reponses_demo[i] = selection

        if not termine_demo:
            if st.button("Valider mes réponses", type="primary"):
                st.session_state["demo_termine"] = True
                st.rerun()
        else:
            liste_reponses = [reponses_demo.get(i) for i in range(len(questions))]
            score, score_max = corriger(questions, liste_reponses)
            st.divider()
            st.subheader(f"Résultat : {score} / {score_max}")
            for i, q in enumerate(questions):
                bonne = q["bonne_reponse_index"]
                donnee = liste_reponses[i]
                if donnee == bonne:
                    st.success(f"**{i + 1}.** {q['enonce']}")
                else:
                    reponse_donnee = q["choix"][donnee] if donnee is not None else "(pas de réponse)"
                    st.error(
                        f"**{i + 1}.** {q['enonce']}\n\nTa réponse : {reponse_donnee}\n\n"
                        f"Bonne réponse : {q['choix'][bonne]}"
                    )
                if q.get("explication"):
                    st.caption(f"{q['explication']}")

            if st.button("Recommencer la démo"):
                st.session_state.pop("demo_reponses", None)
                st.session_state.pop("demo_termine", None)
                st.rerun()

st.divider()
st.subheader("Convaincu ?")
st.write("Crée ton propre espace gratuit, avec tes propres cours, en 2 minutes.")
st.page_link("app.py", label="Commencer maintenant")
