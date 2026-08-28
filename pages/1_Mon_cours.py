"""Page d'un cours : documents, synthèse, quiz."""

from pathlib import Path

import streamlit as st

from core import repository
from core.auth import exiger_identification
from core.chat_service import poser_question
from core.config import EXTENSIONS_DOCUMENTS, EXTENSIONS_IMAGES, UPLOADS_DIR
from core.db import init_db
from core.extraction import extraire_texte, type_fichier_depuis_nom
from core.gemini_client import GeminiNonConfigure, message_utilisateur
from core.quiz_service import generer_quiz
from core.synthese_service import generer_et_sauver_synthese

st.set_page_config(page_title="Mon cours", page_icon="assets/icone.png", layout="centered")
init_db()

identifiant, prenom, api_key = exiger_identification()

cours_id = st.session_state.get("cours_id")
if not cours_id:
    st.warning("Aucun cours sélectionné.")
    if st.button("Retour à l'accueil"):
        st.switch_page("app.py")
    st.stop()

cours = repository.obtenir_cours(cours_id, identifiant)
if not cours:
    st.error("Ce cours n'existe pas ou ne t'appartient pas.")
    if st.button("Retour à l'accueil"):
        st.switch_page("app.py")
    st.stop()

if st.button("Retour à l'accueil"):
    st.switch_page("app.py")

st.title(cours["nom"])
if cours.get("description"):
    st.caption(cours["description"])

tab_docs, tab_synthese, tab_quiz, tab_chat = st.tabs(["Documents", "Synthèse", "Quiz", "Discussion"])

# --- Onglet Documents ---------------------------------------------------------

def _traiter_fichiers(fichiers):
    dossier_cours = UPLOADS_DIR / str(cours_id)
    dossier_cours.mkdir(parents=True, exist_ok=True)

    for fichier in fichiers:
        chemin = dossier_cours / fichier.name
        chemin.write_bytes(fichier.getvalue())

        type_fichier = type_fichier_depuis_nom(fichier.name)
        document_id = repository.ajouter_document(
            cours_id, fichier.name, type_fichier, str(chemin)
        )

        with st.spinner(f"Lecture de « {fichier.name} »..."):
            try:
                texte = extraire_texte(str(chemin), fichier.name, api_key)
                repository.maj_texte_extrait(document_id, texte, statut="ok")
            except GeminiNonConfigure as e:
                repository.maj_texte_extrait(document_id, "", statut="erreur")
                st.error(str(e))
            except Exception as e:
                repository.maj_texte_extrait(document_id, "", statut="erreur")
                st.error(f"Erreur lors de la lecture de « {fichier.name} » : {message_utilisateur(e)}")

    st.success("Fichiers ajoutés.")
    st.rerun()


with tab_docs:
    st.subheader("Déposer des documents")
    st.caption(
        "Deux zones séparées (sur téléphone, ça évite un bug d'Android qui cache "
        "l'accès aux fichiers quand on mélange documents et images)."
    )

    documents_deposes = st.file_uploader(
        "Documents (PDF, Word, PowerPoint, Excel/CSV, notes texte)",
        type=EXTENSIONS_DOCUMENTS,
        accept_multiple_files=True,
        key="upload_documents",
    )
    if documents_deposes and st.button("Ajouter ces documents"):
        _traiter_fichiers(documents_deposes)

    images_deposees = st.file_uploader(
        "Images (captures d'écran, photos de notes manuscrites)",
        type=EXTENSIONS_IMAGES,
        accept_multiple_files=True,
        key="upload_images",
    )
    if images_deposees and st.button("Ajouter ces images"):
        _traiter_fichiers(images_deposees)

    st.divider()
    st.subheader("Documents du cours")
    documents = repository.lister_documents(cours_id)
    if not documents:
        st.info("Aucun document pour l'instant.")
    else:
        badges = {"ok": "Lu", "erreur": "Erreur", "en_attente": "En attente"}
        for doc in documents:
            statut = badges.get(doc["statut_extraction"], doc["statut_extraction"])
            col1, col2 = st.columns([5, 1])
            with col1:
                st.write(f"**{doc['nom_original']}** — {statut}")
            with col2:
                if st.button("Supprimer", key=f"suppr_doc_{doc['id']}"):
                    try:
                        Path(doc["chemin_stocke"]).unlink(missing_ok=True)
                    except Exception:
                        pass
                    repository.supprimer_document(doc["id"])
                    st.rerun()

# --- Onglet Synthèse -----------------------------------------------------------

with tab_synthese:
    synthese = repository.derniere_synthese(cours_id)

    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Fiche de synthèse")
    with col2:
        label = "Régénérer" if synthese else "Générer"
        if st.button(label):
            with st.spinner("L'IA lit tes documents et prépare ta fiche..."):
                try:
                    generer_et_sauver_synthese(cours_id, identifiant, api_key)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {message_utilisateur(e)}")

    if not synthese:
        st.info("Pas encore de synthèse. Ajoute des documents puis clique sur « Générer ».")
    else:
        with st.expander("Synthèse du cours", expanded=True):
            st.markdown(synthese["synthese_md"])
        with st.expander("Pourquoi ce sujet est important"):
            st.markdown(synthese["contexte_md"])
        with st.expander("Notions probables à l'examen"):
            st.markdown(synthese["notions_examen_md"])
        with st.expander("À retenir pour la vie"):
            st.markdown(synthese["a_retenir_md"])
        with st.expander("Anecdotes"):
            st.markdown(synthese["fun_facts_md"])

# --- Onglet Quiz -----------------------------------------------------------------

with tab_quiz:
    st.subheader("Tes 3 quiz")

    quiz_diag = repository.obtenir_quiz_par_type(cours_id, "diagnostique")
    quiz_examen = repository.obtenir_quiz_par_type(cours_id, "examen_blanc")

    tentative_avant = repository.derniere_tentative(quiz_diag["id"], "avant") if quiz_diag else None
    tentative_apres = repository.derniere_tentative(quiz_diag["id"], "apres") if quiz_diag else None

    # --- Carte 1 : diagnostique avant ---
    with st.container(border=True):
        st.markdown("#### 1. Quiz diagnostique (avant révision)")
        st.caption("Pour repérer tes lacunes avant de commencer à réviser.")
        if not quiz_diag:
            if st.button("Générer le quiz diagnostique"):
                with st.spinner("Préparation des questions..."):
                    try:
                        generer_quiz(cours_id, identifiant, "diagnostique", api_key)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {message_utilisateur(e)}")
        elif not tentative_avant:
            if st.button("Passer le quiz (avant révision)"):
                st.session_state["quiz_id"] = quiz_diag["id"]
                st.session_state["phase"] = "avant"
                st.switch_page("pages/2_Quiz.py")
        else:
            st.success(f"Score : {tentative_avant['score']} / {tentative_avant['score_max']}")

    # --- Carte 2 : diagnostique après ---
    with st.container(border=True):
        st.markdown("#### 2. Le même quiz (après révision)")
        st.caption("Repasse-le après avoir révisé pour voir ta progression.")
        if not quiz_diag or not tentative_avant:
            st.info("Passe d'abord le quiz « avant révision ».")
        elif not tentative_apres:
            if st.button("Repasser le quiz (après révision)"):
                st.session_state["quiz_id"] = quiz_diag["id"]
                st.session_state["phase"] = "apres"
                st.switch_page("pages/2_Quiz.py")
        else:
            st.success(f"Score : {tentative_apres['score']} / {tentative_apres['score_max']}")
            if st.button("Voir ma progression"):
                st.session_state["cours_id_progression"] = cours_id
                st.switch_page("pages/3_Progression.py")

    # --- Carte 3 : examen blanc ---
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("#### 3. Examen blanc (chronométré)")
            st.caption("Le quiz le plus corsé, en conditions d'examen.")
        if not quiz_examen:
            if st.button("Générer l'examen blanc"):
                with st.spinner("Préparation de l'examen blanc..."):
                    try:
                        generer_quiz(cours_id, identifiant, "examen_blanc", api_key)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {message_utilisateur(e)}")
        else:
            with col2:
                if st.button("Régénérer", key="regenerer_examen"):
                    with st.spinner("Préparation d'un nouvel examen blanc..."):
                        try:
                            generer_quiz(cours_id, identifiant, "examen_blanc", api_key)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {message_utilisateur(e)}")

            if st.button("Passer l'examen blanc"):
                st.session_state["quiz_id"] = quiz_examen["id"]
                st.session_state["phase"] = "examen_blanc"
                st.switch_page("pages/2_Quiz.py")
            tentatives_examen = repository.lister_tentatives(quiz_examen["id"])
            if tentatives_examen:
                derniere = tentatives_examen[-1]
                st.caption(f"Dernier score : {derniere['score']} / {derniere['score_max']}")

# --- Onglet Discussion -------------------------------------------------------

with tab_chat:
    st.subheader("Pose une question sur ce cours")
    st.caption(
        "L'IA répond en se basant uniquement sur les documents déposés dans ce cours."
    )

    documents_dispo = repository.lister_documents(cours_id)
    if not any(d.get("texte_extrait") for d in documents_dispo):
        st.info("Ajoute au moins un document (onglet Documents) avant de poser une question.")
    else:
        if st.button("Vider la conversation", key="vider_chat"):
            repository.vider_chat(cours_id)
            st.rerun()

        messages = repository.lister_messages_chat(cours_id)
        for message in messages:
            role_affiche = "user" if message["role"] == "utilisateur" else "assistant"
            with st.chat_message(role_affiche):
                st.markdown(message["contenu"])

        question = st.chat_input("Ta question sur le cours...")
        if question:
            with st.chat_message("user"):
                st.markdown(question)
            with st.chat_message("assistant"):
                with st.spinner("Réflexion..."):
                    try:
                        reponse = poser_question(cours_id, identifiant, question, api_key)
                        st.markdown(reponse)
                    except Exception as e:
                        st.error(f"Erreur : {message_utilisateur(e)}")
