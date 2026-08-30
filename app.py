"""Page d'accueil : identification, liste des cours, création d'un nouveau cours."""

import streamlit as st

from core import repository
from core.auth import PROPRIETAIRE_SOLO, exiger_identification, lien_personnel_actuel, oublier_identite
from core.config import LISTE_PAYS
from core.db import init_db
from core.navigation import afficher_navigation

st.set_page_config(
    page_title="Mon assistant de révision",
    page_icon="assets/icone.png",
    layout="centered",
    # Sans ça, le menu (Quiz, Progression, Statistiques...) reste caché derrière une
    # simple flèche en haut à gauche, sans texte - facile à ne jamais remarquer.
    initial_sidebar_state="expanded",
)

init_db()
afficher_navigation()

identifiant, prenom, api_key = exiger_identification()

st.markdown(
    '<p style="font-size:2.8rem; font-weight:800; color:#c9a227; '
    'letter-spacing:0.08em; margin-bottom:-0.6rem;">AKILI</p>',
    unsafe_allow_html=True,
)
st.title("Mon assistant de révision")
st.write("**Pas de panique : révise à ton rythme, je m'occupe du reste.**")
st.caption("Dépose tes notes, génère une synthèse et teste-toi avec des quiz.")

if identifiant != PROPRIETAIRE_SOLO:
    # Mode partagé : plusieurs personnes utilisent la même appli, chacune avec son espace.
    col1, col2 = st.columns([4, 1])
    with col1:
        st.info(f"Connecté en tant que **{prenom}**. Tes cours sont privés, personne d'autre ne les voit.")
    with col2:
        if st.button("Changer de personne"):
            oublier_identite()
            st.rerun()

st.divider()

# --- Formulaire de création d'un cours --------------------------------------
# En premier et déplié tant qu'il n'y a aucun cours : c'est LA première action
# attendue d'un nouvel utilisateur, elle ne doit pas être cachée plus bas derrière
# un clic (retour de test réel : des utilisateurs ne la trouvaient pas).

cours_list = repository.lister_cours(identifiant)

with st.expander("Nouveau cours", expanded=(len(cours_list) == 0)):
    with st.form("nouveau_cours_form", clear_on_submit=True):
        nom = st.text_input("Nom du cours", placeholder="Ex : Introduction au droit des contrats")
        description = st.text_area("Description (optionnel)", placeholder="Quelques mots sur le cours...")
        submitted = st.form_submit_button("Créer le cours")
        if submitted:
            if nom.strip():
                # Emmène directement sur le cours (onglet Documents) au lieu de
                # revenir sur l'accueil : évite le clic "Ouvrir" en plus, qui semble
                # etre le moment ou plusieurs etudiants abandonnaient (cours crees
                # puis jamais aucun document depose - constate sur de vraies donnees).
                nouveau_cours_id = repository.creer_cours(identifiant, nom.strip(), description.strip())
                st.session_state["cours_id"] = nouveau_cours_id
                st.switch_page("pages/1_Mon_cours.py")
            else:
                st.error("Le nom du cours est obligatoire.")

st.divider()

# --- Liste des cours ----------------------------------------------------------

if not cours_list:
    st.info("Aucun cours pour l'instant. Crée ton premier cours ci-dessus.")
else:
    st.subheader("Mes cours")
    for cours in cours_list:
        with st.container(border=True):
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.markdown(f"### {cours['nom']}")
                if cours.get("description"):
                    st.caption(cours["description"])
            with col2:
                if st.button("Ouvrir", key=f"ouvrir_{cours['id']}"):
                    st.session_state["cours_id"] = cours["id"]
                    st.switch_page("pages/1_Mon_cours.py")
            cle_confirmation = f"confirmer_suppr_{cours['id']}"
            with col3:
                if not st.session_state.get(cle_confirmation):
                    if st.button("Supprimer", key=f"supprimer_{cours['id']}"):
                        st.session_state[cle_confirmation] = True
                        st.rerun()

            if st.session_state.get(cle_confirmation):
                st.warning(
                    f"Supprimer « {cours['nom']} » et tout son contenu (documents, "
                    "synthèse, quiz, scores) ? Cette action est définitive."
                )
                col_oui, col_non = st.columns(2)
                with col_oui:
                    if st.button("Oui, supprimer", key=f"confirme_oui_{cours['id']}", type="primary"):
                        repository.supprimer_cours(cours["id"], identifiant)
                        st.session_state.pop(cle_confirmation, None)
                        st.rerun()
                with col_non:
                    if st.button("Annuler", key=f"confirme_non_{cours['id']}"):
                        st.session_state.pop(cle_confirmation, None)
                        st.rerun()

st.divider()

# --- Lien personnel et profil : secondaire, replié, après l'essentiel ---------

if identifiant != PROPRIETAIRE_SOLO:
    lien = lien_personnel_actuel()
    if lien:
        with st.expander("Mon lien personnel (à mettre en favori sur ton téléphone)"):
            st.write(
                "Pendant cette visite, tu n'as plus besoin de retaper quoi que ce soit en "
                "changeant d'onglet. Mais si tu fermes le navigateur, il te faudra ce lien "
                "pour retrouver ton espace la prochaine fois — mets-le en favori maintenant :"
            )
            st.code(lien, language=None)
            st.caption(
                "Garde ce lien de ton côté : sans lui (et sans ton mot de passe), "
                "personne (pas même nous) ne peut retrouver tes cours."
            )

profil_actuel = repository.obtenir_profil(identifiant) or {}
with st.expander("Personnalise l'appli (facultatif)"):
    st.caption(
        "Dis-nous ta filière et ton objectif de vie : la section « à retenir pour "
        "la vie » de tes futures synthèses s'y référera pour te montrer concrètement "
        "en quoi chaque cours te sert, plutôt que des généralités."
    )
    with st.form("profil_form"):
        faculte = st.text_input(
            "Ta faculté / domaine d'études",
            value=profil_actuel.get("faculte") or "",
            placeholder="Ex : Médecine, Droit, Ingénierie civile...",
        )
        reve = st.text_input(
            "Ton rêve dans 20 ans",
            value=profil_actuel.get("reve") or "",
            placeholder="Ex : Devenir chirurgien, ouvrir mon cabinet d'avocat...",
        )
        pays_actuel = profil_actuel.get("pays") or ""
        index_pays = LISTE_PAYS.index(pays_actuel) if pays_actuel in LISTE_PAYS else 0
        pays = st.selectbox("Ton pays", LISTE_PAYS, index=index_pays)
        surnom = st.text_input(
            "Ton surnom (à la fac, au quartier, au travail...)",
            value=profil_actuel.get("surnom") or "",
            placeholder="Ex : Doudou, Ti-Phil...",
            help=(
                "Utile s'il y a plusieurs personnes avec le même prénom que toi : "
                "ça permet au propriétaire de l'appli de savoir à qui il parle, "
                "par exemple pour activer un accès premium."
            ),
        )
        if st.form_submit_button("Enregistrer"):
            repository.sauver_profil(identifiant, faculte.strip(), reve.strip(), pays, surnom.strip())
            st.success("Profil enregistré.")
            st.rerun()

st.divider()
with st.expander("Confidentialité"):
    st.write(
        "Le contenu de tes documents est envoyé à l'API Google Gemini pour être "
        "analysé (résumés, quiz) — c'est le seul endroit où il transite. "
        "Personne d'autre utilisant cette appli ne peut voir tes cours, tes documents "
        "ou tes résultats. Tes données restent accessibles uniquement avec la "
        "combinaison de ton prénom et de ton mot de passe : il n'existe pas de "
        "procédure de récupération si tu perds ton lien personnel et ton mot de passe."
    )

st.page_link("pages/5_Conditions.py", label="Conditions d'utilisation")
