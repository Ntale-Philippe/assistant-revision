"""Identification légère : qui utilise l'appli, et avec quelle clé Gemini.

Deux modes, gérés automatiquement :
- Mode "solo" (usage local sur son propre PC) : une clé Gemini est déjà présente dans
  .streamlit/secrets.toml, aucune identification n'est demandée. Tout est stocké sous
  l'identifiant constant PROPRIETAIRE_SOLO.
- Mode "partagé" (appli hébergée en ligne) : chacun donne juste son prénom et sa
  propre clé Gemini gratuite. Pas de compte, pas de code, pas de mot de passe —
  l'appli est gratuite pour l'instant, le temps de valider qu'elle aide vraiment les
  étudiants avant d'introduire un jour un modèle payant.

L'identifiant qui sépare les données de chacun en base est dérivé de la clé Gemini
elle-même (un hash) : deux clés étant pour ainsi dire toujours différentes, ça suffit
à garantir que personne ne voit les cours de quelqu'un d'autre, sans avoir besoin
d'un champ supplémentaire à saisir.
"""

import hashlib

import streamlit as st

from core.config import get_api_key

PROPRIETAIRE_SOLO = "moi"


def _identifiant_depuis_cle(cle: str) -> str:
    return hashlib.sha256(cle.strip().encode()).hexdigest()[:20]


def get_identity() -> tuple[str | None, str | None, str | None]:
    """Retourne (identifiant, prenom_affiche, cle_api) si connus, sinon (None, None, None)."""
    if "identite" in st.session_state:
        return st.session_state["identite"]

    moi = st.query_params.get("moi", "").strip()
    cle_url = st.query_params.get("cle", "").strip()

    if moi and cle_url:
        resultat = (_identifiant_depuis_cle(cle_url), moi, cle_url)
        st.session_state["identite"] = resultat
        return resultat

    if not moi:
        cle_secrets = get_api_key()
        if cle_secrets:
            # Mode solo classique : pas d'identification nécessaire.
            resultat = (PROPRIETAIRE_SOLO, PROPRIETAIRE_SOLO, cle_secrets)
            st.session_state["identite"] = resultat
            return resultat

    return None, None, None


def exiger_identification() -> tuple[str, str, str]:
    """Renvoie (identifiant, prenom_affiche, cle_api) de la personne courante.

    Si l'identité n'est pas encore connue, affiche un petit formulaire de bienvenue
    et arrête l'exécution de la page (st.stop()) en attendant que la personne le
    remplisse.
    """
    identifiant, prenom, cle_api = get_identity()
    if identifiant and cle_api:
        return identifiant, prenom, cle_api

    st.title("Bienvenue")
    st.write("Avant de commencer, indique ton prénom et ta propre clé Gemini gratuite.")

    st.page_link("pages/6_Demo.py", label="Voir un exemple sans rien remplir")

    st.info(
        "Pas encore de clé ? Va sur https://aistudio.google.com/apikey, connecte-toi "
        "avec ton compte Google, puis clique sur **\"Create API key\"** → "
        "**\"Create API key in new project\"**. C'est gratuit et ça prend 2 minutes."
    )

    with st.form("identification_form"):
        nom = st.text_input("Ton prénom", placeholder="Ex : Alice")
        cle = st.text_input("Ta clé API Gemini", type="password", placeholder="AIza...")
        ok = st.form_submit_button("Commencer")
        if ok:
            if nom.strip() and cle.strip():
                st.query_params["moi"] = nom.strip()
                st.query_params["cle"] = cle.strip()
                st.rerun()
            else:
                st.error("Les deux champs sont obligatoires.")

    st.page_link("pages/5_Conditions.py", label="Conditions d'utilisation")

    st.caption(
        "Astuce : une fois connecté, ton navigateur garde ça en mémoire pour toute la "
        "visite. Pour revenir plus tard sans tout retaper, mets en favori le lien "
        "personnel affiché sur la page d'accueil."
    )

    st.stop()


def oublier_identite():
    """Efface l'identité mémorisée pour cette visite, pour changer de personne."""
    st.session_state.pop("identite", None)
    st.query_params.clear()


def lien_personnel(prenom: str, cle_api: str) -> str:
    """Construit le lien à mettre en favori pour retrouver son espace personnel."""
    from urllib.parse import quote

    return f"?moi={quote(prenom)}&cle={quote(cle_api)}"
