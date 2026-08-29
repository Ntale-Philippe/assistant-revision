"""Insights avancés réservés au propriétaire de l'appli.

Volontairement PAS ajoutée à core/navigation.py : cette page n'apparaît nulle part
dans le menu, donc les étudiants n'ont aucun moyen de savoir qu'elle existe (pas
seulement un mot de passe qu'ils ne peuvent pas deviner — la section entière est
invisible). Le propriétaire y accède en tapant directement l'adresse dans son
navigateur, ex: https://tonapp.streamlit.app/Statistiques_avancees

Protégée par mot de passe (ADMIN_PASSWORD) en plus, au cas où quelqu'un tomberait
sur l'URL par hasard."""

import pandas as pd
import streamlit as st

from core import repository
from core.auth import exiger_identification
from core.config import get_admin_password
from core.db import init_db

st.set_page_config(page_title="Statistiques avancées", page_icon="assets/icone.png", layout="centered")
init_db()
# Pas d'afficher_navigation() ici : pas de menu, pas de lien "Retour à l'accueil"
# qui laisserait deviner qu'il y a un menu caché — la page est volontairement isolée.

identifiant, prenom, api_key = exiger_identification()

st.title("Statistiques avancées")

mot_de_passe_attendu = get_admin_password()
if not mot_de_passe_attendu:
    st.info("Non configuré. Ajoute `ADMIN_PASSWORD` dans les secrets pour activer cette page.")
    st.stop()

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
    st.stop()

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

if insights["repartition_pays"]:
    st.markdown("#### Répartition par pays")
    st.caption("Auto-déclaré dans le profil facultatif — pas de géolocalisation technique.")
    df_pays = pd.DataFrame(
        {"Pays": list(insights["repartition_pays"].keys()), "Étudiants": list(insights["repartition_pays"].values())}
    ).sort_values("Étudiants", ascending=False)
    st.bar_chart(df_pays.set_index("Pays"))

    total_etudiants = df_pays["Étudiants"].sum()
    pays_principal = df_pays.iloc[0]
    st.write(
        f"**Pays principal : {pays_principal['Pays']}** — {pays_principal['Étudiants']} étudiant(s) "
        f"({round(100 * pays_principal['Étudiants'] / total_etudiants)}% du total)"
    )

    detail = insights["detail_par_pays"]
    df_detail = pd.DataFrame(
        [
            {
                "Pays": pays,
                "Étudiants": d["nb_etudiants"],
                "Cours créés": d["nb_cours"],
                "Cours complets (synthèse + quiz)": d["nb_complets"],
                "Taux de complétion": f"{d['taux_completion']}%",
            }
            for pays, d in detail.items()
        ]
    ).sort_values("Étudiants", ascending=False)
    st.dataframe(df_detail, hide_index=True, use_container_width=True)
    st.caption(
        "Le taux de complétion aide à repérer si un pays galère plus que les autres "
        "(connexion, appareils...) — un taux bas avec plusieurs cours peut valoir le coup "
        "d'être creusé."
    )
