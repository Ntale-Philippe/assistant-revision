"""Identification légère : qui utilise l'appli, et avec quelle clé Gemini.

Deux modes, gérés automatiquement :
- Mode "solo" (usage local sur son propre PC) : une clé Gemini est déjà présente dans
  .streamlit/secrets.toml, aucune identification n'est demandée. Tout est stocké sous
  l'identifiant constant PROPRIETAIRE_SOLO.
- Mode "partagé" (appli hébergée en ligne, vendue à plusieurs personnes) : chacun a
  besoin d'un code de licence valide (créé par le vendeur depuis la page Administration
  après un paiement), de son prénom, et de sa propre clé Gemini gratuite. Le code de
  licence est la vraie barrière de paiement : sans lui, impossible d'entrer.
"""

import streamlit as st

from core import repository
from core.config import get_api_key

PROPRIETAIRE_SOLO = "moi"


def _normaliser_code(code: str) -> str:
    return code.strip().lower()


def get_identity() -> tuple[str | None, str | None, str | None]:
    """Retourne (identifiant, prenom_affiche, cle_api) si connus, sinon (None, None, None).

    L'identifiant utilisé pour séparer les données en base est le code de licence
    lui-même (normalisé) : il est unique et attribué par le vendeur, contrairement au
    prénom qui n'est là que pour l'affichage ("Bonjour Alice")."""
    moi = st.query_params.get("moi", "").strip()
    code = _normaliser_code(st.query_params.get("acces", ""))
    cle_url = st.query_params.get("cle", "").strip()

    if moi and code and cle_url:
        licence = repository.obtenir_licence(code)
        if licence and licence["statut"] in ("disponible", "attribuee"):
            if licence["expiree"]:
                return "expiree", moi, cle_url  # sentinelle : jamais une vraie licence
            return code, moi, cle_url
        return "invalide", moi, cle_url  # sentinelle : jamais une vraie licence

    if not moi:
        cle_secrets = get_api_key()
        if cle_secrets:
            # Mode solo classique : pas d'identification nécessaire.
            return PROPRIETAIRE_SOLO, PROPRIETAIRE_SOLO, cle_secrets

    return None, None, None


def exiger_identification() -> tuple[str, str, str]:
    """Renvoie (identifiant, prenom_affiche, cle_api) de la personne courante.

    Si l'identité n'est pas encore connue (ou que le code de licence n'est pas valide),
    affiche un petit formulaire de bienvenue et arrête l'exécution de la page (st.stop())
    en attendant que la personne le remplisse avec un code valide.
    """
    identifiant, prenom, cle_api = get_identity()

    if identifiant == "invalide":
        st.error(
            "Ce code d'accès n'est pas valide ou a été désactivé. "
            "Contacte la personne qui te l'a fourni."
        )
        st.stop()

    if identifiant == "expiree":
        st.error(
            "Ton accès a expiré. Contacte la personne qui te l'a fourni pour le renouveler."
        )
        st.stop()

    if identifiant and cle_api:
        if identifiant != PROPRIETAIRE_SOLO:
            repository.activer_licence(identifiant, prenom)
        return identifiant, prenom, cle_api

    st.title("Bienvenue")
    st.write(
        "Avant de commencer, indique ton prénom, le code d'accès que tu as reçu après "
        "ton paiement, et ta propre clé Gemini gratuite."
    )
    st.info(
        "Pas encore de clé ? Va sur https://aistudio.google.com/apikey, connecte-toi "
        "avec ton compte Google, puis clique sur **\"Create API key\"** → "
        "**\"Create API key in new project\"**. C'est gratuit et ça prend 2 minutes."
    )

    with st.form("identification_form"):
        nom = st.text_input("Ton prénom", placeholder="Ex : Alice")
        code_saisi = st.text_input(
            "Ton code d'accès",
            placeholder="Reçu après ton paiement",
            help="Fourni uniquement après paiement. Sans ce code, impossible d'entrer.",
        )
        cle = st.text_input("Ta clé API Gemini", type="password", placeholder="AIza...")
        ok = st.form_submit_button("Commencer")
        if ok:
            if nom.strip() and code_saisi.strip() and cle.strip():
                st.query_params["moi"] = nom.strip()
                st.query_params["acces"] = code_saisi.strip()
                st.query_params["cle"] = cle.strip()
                st.rerun()
            else:
                st.error("Les trois champs sont obligatoires.")

    st.stop()


def lien_personnel(prenom: str, code_acces: str, cle_api: str) -> str:
    """Construit le lien à mettre en favori pour retrouver son espace personnel."""
    from urllib.parse import quote

    return f"?moi={quote(prenom)}&acces={quote(code_acces)}&cle={quote(cle_api)}"
