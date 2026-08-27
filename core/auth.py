"""Identification légère : qui utilise l'appli, et avec quelle clé Gemini.

Deux modes, gérés automatiquement :
- Mode "solo" (usage local sur son propre PC) : une clé Gemini est déjà présente dans
  .streamlit/secrets.toml, aucune identification n'est demandée. Tout est stocké sous
  l'identifiant constant PROPRIETAIRE_SOLO.
- Mode "partagé" (appli hébergée en ligne, utilisée par plusieurs personnes) : chacun
  ouvre l'appli avec un lien personnel contenant son prénom, un code d'accès personnel
  qu'il a choisi, et sa propre clé Gemini (paramètres d'URL ?moi=...&acces=...&cle=...).

Le prénom seul ne sert qu'à l'affichage ("Bonjour Alice") : ce qui sépare vraiment les
données de chacun, c'est la combinaison prénom + code d'accès. Sans ça, deux personnes
qui entrent le même prénom (très fréquent) se retrouveraient à voir les mêmes cours,
ou n'importe qui pourrait deviner un prénom pour accéder aux cours d'un autre.
"""

import streamlit as st

from core.config import get_api_key

PROPRIETAIRE_SOLO = "moi"


def _construire_identifiant(prenom: str, code_acces: str) -> str:
    """Combine prénom + code d'accès en un identifiant unique utilisé en base de données."""
    return f"{prenom.strip().lower()}#{code_acces.strip().lower()}"


def get_identity() -> tuple[str | None, str | None, str | None]:
    """Retourne (identifiant, prenom_affiche, cle_api) si connus, sinon (None, None, None)."""
    moi = st.query_params.get("moi", "").strip()
    acces = st.query_params.get("acces", "").strip()
    cle_url = st.query_params.get("cle", "").strip()

    if moi and acces and cle_url:
        return _construire_identifiant(moi, acces), moi, cle_url

    if not moi:
        cle_secrets = get_api_key()
        if cle_secrets:
            # Mode solo classique : pas d'identification nécessaire.
            return PROPRIETAIRE_SOLO, PROPRIETAIRE_SOLO, cle_secrets

    return None, None, None


def exiger_identification() -> tuple[str, str, str]:
    """Renvoie (identifiant, prenom_affiche, cle_api) de la personne courante.

    Si l'identité n'est pas encore connue, affiche un petit formulaire de bienvenue
    et arrête l'exécution de la page (st.stop()) en attendant que la personne le remplisse.
    """
    identifiant, prenom, cle_api = get_identity()
    if identifiant and cle_api:
        return identifiant, prenom, cle_api

    st.title("Bienvenue")
    st.write(
        "Avant de commencer, indique ton prénom, invente un code d'accès personnel "
        "(pour que tes cours restent privés, même si quelqu'un d'autre a le même "
        "prénom), et donne ta propre clé Gemini gratuite."
    )
    st.info(
        "Pas encore de clé ? Va sur https://aistudio.google.com/apikey, connecte-toi "
        "avec ton compte Google, puis clique sur **\"Create API key\"** → "
        "**\"Create API key in new project\"**. C'est gratuit et ça prend 2 minutes."
    )

    with st.form("identification_form"):
        nom = st.text_input("Ton prénom", placeholder="Ex : Alice")
        code = st.text_input(
            "Ton code d'accès personnel",
            type="password",
            placeholder="Un mot ou une phrase que toi seul connais",
            help=(
                "Note-le bien quelque part : c'est lui qui protège tes cours. "
                "Il n'y a pas de \"mot de passe oublié\"."
            ),
        )
        cle = st.text_input("Ta clé API Gemini", type="password", placeholder="AIza...")
        ok = st.form_submit_button("Commencer")
        if ok:
            if nom.strip() and code.strip() and cle.strip():
                st.query_params["moi"] = nom.strip()
                st.query_params["acces"] = code.strip()
                st.query_params["cle"] = cle.strip()
                st.rerun()
            else:
                st.error("Les trois champs sont obligatoires.")

    st.stop()


def lien_personnel(prenom: str, code_acces: str, cle_api: str) -> str:
    """Construit le lien à mettre en favori pour retrouver son espace personnel."""
    from urllib.parse import quote

    return f"?moi={quote(prenom)}&acces={quote(code_acces)}&cle={quote(cle_api)}"
