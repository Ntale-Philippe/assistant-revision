"""Page de statistiques : chiffres personnels et globaux pour tout le monde, et
insights avancés (protégés par mot de passe) réservés au propriétaire de l'appli."""

import pandas as pd
import streamlit as st

from core import repository
from core.auth import exiger_identification
from core.config import get_admin_password
from core.db import init_db
from core.navigation import afficher_navigation

st.set_page_config(page_title="Statistiques", page_icon="assets/icone.png", layout="centered")
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

st.divider()

# --- Statistiques avancées (propriétaire uniquement) ---------------------------

st.subheader("Statistiques avancées (réservé au propriétaire)")

mot_de_passe_attendu = get_admin_password()
if not mot_de_passe_attendu:
    st.info("Non configuré. Ajoute `ADMIN_PASSWORD` dans les secrets pour activer cette section.")
else:
    deverrouille = st.session_state.get("stats_admin_ok", False)

    if not deverrouille:
        with st.form("mot_de_passe_admin_form"):
            saisi = st.text_input("Mot de passe administrateur", type="password")
            if st.form_submit_button("Déverrouiller"):
                if saisi == mot_de_passe_attendu:
                    st.session_state["stats_admin_ok"] = True
                    st.rerun()
                else:
                    st.error("Mot de passe incorrect.")
    else:
        if st.button("Verrouiller à nouveau"):
            st.session_state.pop("stats_admin_ok", None)
            st.rerun()

        insights = repository.insights_admin()
        total = insights["nb_cours_total"]
        n_vides = len(insights["cours_vides"])
        n_sans_synthese = len(insights["cours_sans_synthese"])
        n_sans_quiz = len(insights["cours_sans_quiz"])
        n_complets = max(0, total - n_vides - n_sans_synthese - n_sans_quiz)

        st.markdown("#### Où les étudiants s'arrêtent (entonnoir d'utilisation)")
        if total == 0:
            st.info("Aucun cours pour l'instant (hors ton compte solo et la démo).")
        else:
            st.write(f"**{total} cours créés** au total :")
            st.write(f"- 🔴 **{n_vides}** sans aucun document déposé (bloqués dès le départ)")
            st.write(f"- 🟠 **{n_sans_synthese}** avec des documents, mais aucune synthèse générée")
            st.write(f"- 🟡 **{n_sans_quiz}** avec une synthèse, mais aucun quiz généré")
            st.write(f"- 🟢 **{n_complets}** avec synthèse ET quiz (utilisation complète)")

            cours_a_relancer = insights["cours_vides"] + insights["cours_sans_synthese"] + insights["cours_sans_quiz"]
            if cours_a_relancer:
                with st.expander(f"Voir les {len(cours_a_relancer)} cours bloqués (à relancer si besoin)"):
                    for c in cours_a_relancer:
                        st.caption(f"« {c['nom']} » — créé le {c['created_at']} — étudiant {c['proprietaire'][:8]}...")

        if insights["documents_en_erreur"]:
            st.markdown("#### Documents en échec de lecture")
            for d in insights["documents_en_erreur"]:
                st.caption(f"« {d['document']} » (cours « {d['cours']} », étudiant {d['proprietaire'][:8]}...)")
        else:
            st.markdown("#### Documents en échec de lecture")
            st.caption("Aucun — tous les documents déposés ont été lus avec succès.")

        if insights["scores_par_type"]:
            st.markdown("#### Score moyen par type de quiz")
            noms_types = {
                "diagnostique": "Quiz diagnostique (avant/après)",
                "examen_blanc": "Examen blanc",
                "reponse_ecrite": "Examen écrit",
            }
            for type_quiz, score in insights["scores_par_type"].items():
                st.write(f"- **{noms_types.get(type_quiz, type_quiz)}** : {score}%")

        if insights["cours_par_jour"]:
            st.markdown("#### Croissance (cours créés par jour)")
            df = pd.DataFrame(
                {"Jour": list(insights["cours_par_jour"].keys()), "Cours créés": list(insights["cours_par_jour"].values())}
            )
            st.bar_chart(df.set_index("Jour"))
