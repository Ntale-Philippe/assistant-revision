"""Identification légère : qui utilise l'appli, et avec quelle clé Gemini.

Deux modes, gérés automatiquement :
- Mode "solo" (usage local sur son propre PC) : une clé Gemini est déjà présente dans
  .streamlit/secrets.toml, aucune identification n'est demandée. Tout est stocké sous
  le pseudo constant PROPRIETAIRE_SOLO.
- Mode "partagé" (appli hébergée en ligne, utilisée par plusieurs personnes) : chacun
  ouvre l'appli avec un lien personnel contenant son prénom et sa propre clé Gemini
  (paramètres d'URL ?moi=...&cle=...). Ça sépare complètement les cours/quiz de chacun,
  sans compte ni mot de passe.
"""

import streamlit as st

from core.config import get_api_key

PROPRIETAIRE_SOLO = "moi"


def get_identity() -> tuple[str | None, str | None]:
    """Retourne (pseudo, cle_api) si connus, sinon (None, None)."""
    moi = st.query_params.get("moi", "").strip()
    cle_url = st.query_params.get("cle", "").strip()

    if moi and cle_url:
        return moi, cle_url

    if not moi:
        cle_secrets = get_api_key()
        if cle_secrets:
            # Mode solo classique : pas d'identification nécessaire.
            return PROPRIETAIRE_SOLO, cle_secrets

    return None, None


def exiger_identification() -> tuple[str, str]:
    """Renvoie (pseudo, cle_api) de la personne courante.

    Si l'identité n'est pas encore connue, affiche un petit formulaire de bienvenue
    et arrête l'exécution de la page (st.stop()) en attendant que la personne le remplisse.
    """
    pseudo, cle_api = get_identity()
    if pseudo and cle_api:
        return pseudo, cle_api

    st.title("👋 Bienvenue !")
    st.write(
        "Avant de commencer, dis-moi comment tu t'appelles et donne ta propre clé "
        "Gemini gratuite (comme ça, tes cours restent privés et personne d'autre "
        "n'utilise ton quota gratuit)."
    )
    st.info(
        "Pas encore de clé ? Va sur https://aistudio.google.com/apikey, connecte-toi "
        "avec ton compte Google, puis clique sur **\"Create API key\"** → "
        "**\"Create API key in new project\"**. C'est gratuit et ça prend 2 minutes.",
        icon="🔑",
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

    st.stop()


def lien_personnel(pseudo: str, cle_api: str) -> str:
    """Construit le lien à mettre en favori pour retrouver son espace personnel."""
    from urllib.parse import quote

    return f"?moi={quote(pseudo)}&cle={quote(cle_api)}"
