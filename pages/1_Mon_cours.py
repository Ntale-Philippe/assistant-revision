"""Page d'un cours : documents, synthèse, quiz."""

from pathlib import Path

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from core import repository
from core.auth import exiger_identification
from core.chat_service import poser_question
from core.config import (
    DEVISE_PREMIUM,
    DUREE_PREMIUM_JOURS,
    EXTENSIONS_DOCUMENTS,
    EXTENSIONS_IMAGES,
    NB_QUESTIONS_CHAT_GRATUIT,
    PRIX_PREMIUM,
    SEUIL_AVERTISSEMENT_CARACTERES,
    SEUIL_ENORME_CARACTERES,
    SEUIL_LIMITE_TECHNIQUE_CARACTERES,
    UPLOADS_DIR,
)
from core.db import init_db
from core.extraction import extraire_texte, type_fichier_depuis_nom
from core.gemini_client import GeminiNonConfigure
from core.gemini_client import message_utilisateur as message_utilisateur_gemini
from core.gemini_client import peut_reessayer, signaler_echec, signaler_succes
from core.mistral_client import message_utilisateur as message_utilisateur_mistral
from core.navigation import afficher_navigation
from core.quiz_service import generer_quiz, generer_quiz_ecrit
from core.synthese_service import generer_et_sauver_synthese

st.set_page_config(
    page_title="Mon cours", page_icon="assets/icone.png", layout="centered",
    initial_sidebar_state="expanded",
)
init_db()
afficher_navigation()

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

def _message_guide(cours_id: int):
    """Montre toujours LA prochaine étape la plus utile pour CE cours précis, plutôt
    qu'un mode d'emploi générique figé qui ne s'affichait qu'une fois (avant le tout
    premier document). Comme ça, un étudiant qui revient après 3 jours sait quoi
    faire sans avoir à se souvenir où il en était - et une fois les bases explorées,
    le message disparaît tout seul pour ne pas alourdir l'appli à chaque visite."""
    if not repository.lister_documents(cours_id):
        st.info("📄 Dépose au moins un document dans l'onglet **Documents** pour commencer.")
        return
    if not repository.derniere_synthese(cours_id):
        st.info("🧠 Génère ta fiche de synthèse dans l'onglet **Synthèse**.")
        return
    quiz_diag = repository.obtenir_quiz_par_type(cours_id, "diagnostique")
    if not quiz_diag:
        st.info("✅ Teste tes connaissances avec le quiz diagnostique, dans l'onglet **Quiz**.")
        return
    if not repository.derniere_tentative(quiz_diag["id"], "avant"):
        st.info("▶️ Passe le quiz diagnostique (onglet **Quiz**) pour voir où tu en es avant de réviser.")
        return
    if not repository.derniere_tentative(quiz_diag["id"], "apres"):
        st.info("📚 Révise avec ta fiche de synthèse, puis repasse le même quiz pour mesurer ta progression.")
        return
    if not repository.lister_messages_chat(cours_id):
        st.info("💬 Une question sur ce cours ? Essaie l'onglet **Discussion** — l'IA répond à partir de tes documents.")
        return
    # Les bases ont toutes été essayées au moins une fois : plus rien à suggérer.


_message_guide(cours_id)

est_premium = repository.a_acces_debloque(identifiant)

tab_docs, tab_synthese, tab_quiz, tab_chat = st.tabs(["Documents", "Synthèse", "Quiz", "Discussion"])


def _message_premium(quoi: str):
    """Message affiché à la place d'une fonctionnalité payante non débloquée."""
    st.warning(
        f"🔒 {quoi} — fonctionnalité payante ({PRIX_PREMIUM}$ pour {DUREE_PREMIUM_JOURS} jours). "
        "Envoie le paiement par mobile money et préviens le propriétaire de l'appli pour débloquer."
    )


def _etat_bouton_ia(cle: str) -> tuple[bool, int]:
    """Vérifie si le bouton lié à `cle` peut être cliqué (pas de cooldown en cours).

    Si un cooldown est actif, déclenche un petit auto-rafraîchissement pour que le
    bouton se réactive tout seul, sans que l'utilisateur ait besoin de recliquer
    ailleurs sur la page."""
    peut, restant = peut_reessayer(cle)
    if not peut:
        st_autorefresh(interval=1000, limit=restant + 1, key=f"cooldown_{cle}")
    return peut, restant


def _executer_generation_ia(cle: str, action, cle_celebration: str | None = None):
    """Exécute une génération IA (synthèse/quiz, via Mistral), avec suivi du cooldown
    en cas d'échec.

    En cas de succès : efface le cooldown et rafraîchit la page. Si `cle_celebration`
    est fourni, retient qu'il faudra célébrer (st.balloons()) juste après le rechargement
    — impossible de le faire ici directement, le st.rerun() juste après l'effacerait.
    En cas d'échec : démarre un cooldown (pour empêcher de recliquer tout de suite,
    ce qui aggraverait un ralentissement passager), et RETIENT le message d'erreur
    en session (sinon le compte à rebours du cooldown, qui rafraîchit la page chaque
    seconde, l'efface presque aussitôt affiché)."""
    try:
        action()
        signaler_succes(cle)
        st.session_state.pop(f"derniere_erreur_{cle}", None)
        if cle_celebration:
            st.session_state[cle_celebration] = True
        st.rerun()
    except Exception as e:
        signaler_echec(cle)
        st.session_state[f"derniere_erreur_{cle}"] = message_utilisateur_mistral(e)
        st.rerun()


def _afficher_cooldown(cle: str, peut: bool, restant: int):
    """Affiche le compte à rebours et, s'il y en a une, la dernière erreur rencontrée
    (voir _executer_generation_ia pour pourquoi elle est stockée en session)."""
    if peut:
        return
    st.caption(f"Patiente {restant}s avant de recliquer (évite d'aggraver un ralentissement de l'IA).")
    derniere_erreur = st.session_state.get(f"derniere_erreur_{cle}")
    if derniere_erreur:
        st.error(f"Erreur : {derniere_erreur}")


def _avertir_si_cours_volumineux():
    """Affiche un avertissement si le cours contient beaucoup de texte : une seule
    génération (tout le texte envoyé en un seul appel, jamais découpé) prendra plus
    longtemps à répondre pour un cours énorme."""
    texte_cours = repository.texte_complet_du_cours(cours_id)
    if len(texte_cours) > SEUIL_LIMITE_TECHNIQUE_CARACTERES:
        st.error(
            "Ce cours dépasse la limite technique de l'IA (trop de texte pour être "
            "lu en une seule fois) : la génération va très probablement échouer. "
            "**Il faut diviser ce cours en plusieurs cours plus petits** (par "
            "chapitre, par exemple) — réessayer ne suffira pas."
        )
    elif len(texte_cours) > SEUIL_ENORME_CARACTERES:
        st.warning(
            "Ce cours est énorme (l'équivalent d'un manuel entier) : une seule "
            "génération peut prendre nettement plus longtemps que d'habitude. "
            "Envisage de le diviser en plusieurs cours plus petits (par chapitre, "
            "par exemple) pour des réponses plus rapides."
        )
    elif len(texte_cours) > SEUIL_AVERTISSEMENT_CARACTERES:
        st.warning(
            "Ce cours contient beaucoup de texte (plusieurs documents, ou des "
            "documents volumineux) : la génération peut prendre un peu plus de "
            "temps que d'habitude. C'est normal — patiente sans recliquer plusieurs fois."
        )

# --- Onglet Documents ---------------------------------------------------------

def _sauver_fichier_sur_disque(nom: str, contenu: bytes) -> str:
    dossier_cours = UPLOADS_DIR / str(cours_id)
    dossier_cours.mkdir(parents=True, exist_ok=True)
    chemin = dossier_cours / nom
    chemin.write_bytes(contenu)
    return str(chemin)


def _extraire_et_sauver_texte(document_id: int, chemin: str, nom: str):
    with st.spinner(f"Lecture de « {nom} »..."):
        try:
            texte = extraire_texte(chemin, nom, api_key)
            repository.maj_texte_extrait(document_id, texte, statut="ok")
        except GeminiNonConfigure as e:
            repository.maj_texte_extrait(document_id, "", statut="erreur")
            st.error(str(e))
        except Exception as e:
            repository.maj_texte_extrait(document_id, "", statut="erreur")
            st.error(f"Erreur lors de la lecture de « {nom} » : {message_utilisateur_gemini(e)}")


def _traiter_fichiers(fichiers, categorie="cours"):
    """Ajoute les fichiers, mais si un document du même nom existe déjà dans ce
    cours, ne l'écrase pas silencieusement : le met de côté et demande à
    l'utilisateur (via _afficher_doublons_en_attente) s'il veut le remplacer ou
    annuler cet ajout précis."""
    cle_doublons = f"doublons_{categorie}"
    doublons_en_attente = st.session_state.setdefault(cle_doublons, [])
    nouveaux_traites = False

    for fichier in fichiers:
        existant = repository.obtenir_document_par_nom(cours_id, fichier.name, categorie)
        if existant:
            if not any(d["nom"] == fichier.name for d in doublons_en_attente):
                doublons_en_attente.append({
                    "nom": fichier.name,
                    "contenu": fichier.getvalue(),
                    "document_id": existant["id"],
                })
            continue

        chemin = _sauver_fichier_sur_disque(fichier.name, fichier.getvalue())
        type_fichier = type_fichier_depuis_nom(fichier.name)
        document_id = repository.ajouter_document(cours_id, fichier.name, type_fichier, chemin, categorie=categorie)
        _extraire_et_sauver_texte(document_id, chemin, fichier.name)
        nouveaux_traites = True

    if nouveaux_traites:
        st.success("Fichiers ajoutés.")
    st.rerun()


def _afficher_doublons_en_attente(categorie="cours"):
    """Affiche, pour chaque fichier mis de côté par _traiter_fichiers car un
    document du même nom existe déjà, un choix explicite : remplacer le document
    existant (relit le nouveau fichier) ou annuler cet ajout (ne touche à rien)."""
    cle_doublons = f"doublons_{categorie}"
    doublons = st.session_state.get(cle_doublons, [])
    for d in list(doublons):
        st.warning(f"Le document « {d['nom']} » est déjà dans ton cours. Que veux-tu faire ?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Remplacer le fichier existant", key=f"remplacer_{categorie}_{d['nom']}"):
                chemin = _sauver_fichier_sur_disque(d["nom"], d["contenu"])
                _extraire_et_sauver_texte(d["document_id"], chemin, d["nom"])
                doublons.remove(d)
                st.session_state[cle_doublons] = doublons
                st.rerun()
        with col2:
            if st.button("Annuler cet ajout", key=f"annuler_{categorie}_{d['nom']}"):
                doublons.remove(d)
                st.session_state[cle_doublons] = doublons
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

    _afficher_doublons_en_attente("cours")

    st.divider()
    with st.expander("Anciens examens (facultatif)"):
        if not est_premium:
            _message_premium("Déposer d'anciens examens")
        else:
            st.caption(
                "Dépose ici de vrais anciens examens de ce cours, si tu en as : l'IA s'en "
                "sert en priorité pour deviner les vraies notions probables et pour "
                "composer des quiz dans le style de ton professeur. Ils ne sont jamais "
                "mélangés au contenu du cours lui-même."
            )
            examens_documents = st.file_uploader(
                "Anciens examens — documents",
                type=EXTENSIONS_DOCUMENTS,
                accept_multiple_files=True,
                key="upload_examens_documents",
            )
            if examens_documents and st.button("Ajouter ces examens (documents)"):
                _traiter_fichiers(examens_documents, categorie="examen_passe")

            examens_images = st.file_uploader(
                "Anciens examens — images (photos de sujets papier)",
                type=EXTENSIONS_IMAGES,
                accept_multiple_files=True,
                key="upload_examens_images",
            )
            if examens_images and st.button("Ajouter ces examens (images)"):
                _traiter_fichiers(examens_images, categorie="examen_passe")

            _afficher_doublons_en_attente("examen_passe")

    st.divider()
    st.subheader("Documents du cours")
    documents = repository.lister_documents(cours_id)
    if not documents:
        st.info("Aucun document pour l'instant.")
    else:
        badges = {"ok": "Lu", "erreur": "Erreur", "en_attente": "En attente"}
        for doc in documents:
            statut = badges.get(doc["statut_extraction"], doc["statut_extraction"])
            etiquette = " · ancien examen" if doc.get("categorie") == "examen_passe" else ""
            col1, col2 = st.columns([5, 1])
            with col1:
                st.write(f"**{doc['nom_original']}** — {statut}{etiquette}")
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
    _avertir_si_cours_volumineux()

    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Fiche de synthèse")
    with col2:
        cle_cooldown = f"synthese_{cours_id}"
        peut, restant = _etat_bouton_ia(cle_cooldown)
        # La 1re génération est gratuite ; régénérer (déjà une synthèse) est payant.
        verrouille = bool(synthese) and not est_premium
        label = "Régénérer" if synthese else "Générer"
        if st.button(label, disabled=not peut or verrouille):
            with st.spinner("L'IA lit tes documents et prépare ta fiche..."):
                _executer_generation_ia(
                    cle_cooldown,
                    lambda: generer_et_sauver_synthese(cours_id, identifiant),
                    cle_celebration=f"celebrer_synthese_{cours_id}" if not synthese else None,
                )
    if verrouille:
        _message_premium("Régénérer la synthèse")
    _afficher_cooldown(cle_cooldown, peut, restant)

    if st.session_state.pop(f"celebrer_synthese_{cours_id}", False):
        st.balloons()
        st.success("Ta première fiche de synthèse est prête ! 🎉")

    if not synthese:
        if repository.lister_documents(cours_id):
            # Documents déjà là : le seul mot qui manque, c'est "clique" - dire à
            # nouveau "ajoute des documents" ferait croire que le dépôt a échoué.
            st.info("Clique sur « Générer » ci-dessus pour créer ta fiche de synthèse.")
        else:
            st.info("Ajoute d'abord un document (onglet Documents), puis clique sur « Générer ».")
    else:
        st.caption("À lire dans l'ordre : le résumé d'abord, le reste pour approfondir.")
        with st.expander("Synthèse du cours", expanded=True, icon=":material/summarize:"):
            st.markdown(synthese["synthese_md"])
        with st.expander("Pourquoi ce sujet est important", icon=":material/lightbulb:"):
            st.markdown(synthese["contexte_md"])
        with st.expander("Notions probables à l'examen", icon=":material/target:"):
            st.markdown(synthese["notions_examen_md"])
        with st.expander("À retenir pour la vie", icon=":material/favorite:"):
            st.caption("💫 Des faits et petites histoires intéressants à connaître, au-delà de l'examen.")
            st.markdown(synthese["a_retenir_md"])
        with st.expander("Anecdotes", icon=":material/auto_awesome:"):
            st.markdown(synthese["fun_facts_md"])

# --- Onglet Quiz -----------------------------------------------------------------

with tab_quiz:
    st.subheader("Tes modes de révision")
    _avertir_si_cours_volumineux()

    quiz_diag = repository.obtenir_quiz_par_type(cours_id, "diagnostique")
    quiz_examen = repository.obtenir_quiz_par_type(cours_id, "examen_blanc")
    quiz_ecrit = repository.obtenir_quiz_par_type(cours_id, "reponse_ecrite")

    tentative_avant = repository.derniere_tentative(quiz_diag["id"], "avant") if quiz_diag else None
    tentative_apres = repository.derniere_tentative(quiz_diag["id"], "apres") if quiz_diag else None

    # --- Carte 1 : diagnostique avant ---
    with st.container(border=True):
        st.markdown("#### 1. Quiz diagnostique (avant révision)")
        st.caption("Pour repérer tes lacunes avant de commencer à réviser.")
        if not quiz_diag:
            cle_cooldown = f"quiz_diag_{cours_id}"
            peut, restant = _etat_bouton_ia(cle_cooldown)
            if st.button("Générer le quiz diagnostique", disabled=not peut):
                with st.spinner("Préparation des questions..."):
                    _executer_generation_ia(
                        cle_cooldown,
                        lambda: generer_quiz(cours_id, identifiant, "diagnostique"),
                    )
            _afficher_cooldown(cle_cooldown, peut, restant)
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
        if not est_premium:
            _message_premium("L'examen blanc")
        else:
            cle_cooldown = f"examen_{cours_id}"
            peut, restant = _etat_bouton_ia(cle_cooldown)
            if not quiz_examen:
                if st.button("Générer l'examen blanc", disabled=not peut):
                    with st.spinner("Préparation de l'examen blanc..."):
                        _executer_generation_ia(
                            cle_cooldown,
                            lambda: generer_quiz(cours_id, identifiant, "examen_blanc"),
                        )
                _afficher_cooldown(cle_cooldown, peut, restant)
            else:
                with col2:
                    if st.button("Régénérer", key="regenerer_examen", disabled=not peut):
                        with st.spinner("Préparation d'un nouvel examen blanc..."):
                            _executer_generation_ia(
                                cle_cooldown,
                                lambda: generer_quiz(cours_id, identifiant, "examen_blanc"),
                            )
                _afficher_cooldown(cle_cooldown, peut, restant)

                if st.button("Passer l'examen blanc"):
                    st.session_state["quiz_id"] = quiz_examen["id"]
                    st.session_state["phase"] = "examen_blanc"
                    st.switch_page("pages/2_Quiz.py")
                tentatives_examen = repository.lister_tentatives(quiz_examen["id"])
                if tentatives_examen:
                    derniere = tentatives_examen[-1]
                    st.caption(f"Dernier score : {derniere['score']} / {derniere['score_max']}")

    # --- Carte 4 : questions à réponse écrite ---
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("#### 4. Examen écrit (chronométré)")
            st.caption(
                "Rédige tes réponses au lieu de choisir, en temps limité — corrigé "
                "par l'IA. Séparé des 3 quiz ci-dessus, ne compte pas dans ta progression."
            )
        if not est_premium:
            _message_premium("L'examen écrit")
        else:
            cle_cooldown = f"quiz_ecrit_{cours_id}"
            peut, restant = _etat_bouton_ia(cle_cooldown)
            if not quiz_ecrit:
                if st.button("Générer les questions", disabled=not peut):
                    with st.spinner("Préparation des questions..."):
                        _executer_generation_ia(
                            cle_cooldown,
                            lambda: generer_quiz_ecrit(cours_id, identifiant),
                        )
                _afficher_cooldown(cle_cooldown, peut, restant)
            else:
                with col2:
                    if st.button("Régénérer", key="regenerer_ecrit", disabled=not peut):
                        with st.spinner("Préparation de nouvelles questions..."):
                            _executer_generation_ia(
                                cle_cooldown,
                                lambda: generer_quiz_ecrit(cours_id, identifiant),
                            )
                _afficher_cooldown(cle_cooldown, peut, restant)

                if st.button("Passer l'examen écrit"):
                    st.session_state["quiz_ecrit_id"] = quiz_ecrit["id"]
                    st.switch_page("pages/7_Questions_ecrites.py")
                tentatives_ecrit = repository.lister_tentatives(quiz_ecrit["id"])
                if tentatives_ecrit:
                    derniere = tentatives_ecrit[-1]
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

        nb_questions_posees = repository.compter_questions_chat(cours_id)
        if not est_premium and nb_questions_posees >= NB_QUESTIONS_CHAT_GRATUIT:
            _message_premium("Continuer cette discussion")
        else:
            if not est_premium:
                restant_gratuit = NB_QUESTIONS_CHAT_GRATUIT - nb_questions_posees
                st.caption(
                    f"🔓 Version gratuite : encore {restant_gratuit} question"
                    f"{'s' if restant_gratuit > 1 else ''} avant de passer en premium."
                )
            question = st.chat_input("Ta question sur le cours...")
            if question:
                with st.chat_message("user"):
                    st.markdown(question)
                with st.chat_message("assistant"):
                    with st.spinner("Réflexion..."):
                        try:
                            poser_question(cours_id, identifiant, question)
                            # Sans ce rerun, la nouvelle question et sa réponse restaient
                            # affichées EN DESSOUS du champ de saisie (il est appelé avant
                            # ce bloc dans le code) jusqu'à la prochaine interaction — le
                            # champ ne semblait donc pas toujours en bas de la conversation.
                            # Le rerun relit tout de suite l'historique complet (avec ce
                            # nouvel échange déjà sauvegardé), qui s'affiche alors bien
                            # AVANT le champ de saisie, comme attendu.
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {message_utilisateur_mistral(e)}")
