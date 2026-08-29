"""Identification légère : qui utilise l'appli.

Deux modes, gérés automatiquement :
- Mode "solo" (usage local sur son propre PC) : une clé Gemini est déjà présente dans
  .streamlit/secrets.toml, aucune identification n'est demandée. Tout est stocké sous
  l'identifiant constant PROPRIETAIRE_SOLO.
- Mode "partagé" (appli hébergée en ligne) : chacun donne juste son prénom et invente
  un mot de passe personnel. Aucune clé Gemini à créer, aucun compte : l'appli utilise
  UNE SEULE clé Gemini partagée entre tous les visiteurs (configurée par le
  propriétaire de l'appli, jamais vue par les étudiants). C'est ce qui rend l'appli
  utilisable en moins d'une minute, même par quelqu'un qui ne connaît rien à la
  programmation.

L'identifiant qui sépare les données de chacun en base est dérivé d'un hash du
prénom + mot de passe : ça suffit à garantir que deux personnes ne voient jamais les
mêmes cours, sans avoir besoin d'un vrai système de comptes.
"""

import hashlib

import streamlit as st

from core import repository
from core.config import get_api_key, get_shared_api_key

PROPRIETAIRE_SOLO = "moi"


def _identifiant(prenom: str, mot_de_passe: str) -> str:
    brut = f"{prenom.strip().lower()}::{mot_de_passe.strip()}"
    return hashlib.sha256(brut.encode()).hexdigest()[:20]


def get_identity() -> tuple[str | None, str | None, str | None]:
    """Retourne (identifiant, prenom_affiche, cle_api) si connus, sinon (None, None, None)."""
    if "identite" in st.session_state:
        return st.session_state["identite"]

    moi = st.query_params.get("moi", "").strip()
    mot = st.query_params.get("mot", "").strip()

    if moi and mot:
        cle_partagee = get_shared_api_key()
        if not cle_partagee:
            return None, None, None
        identifiant = _identifiant(moi, mot)
        resultat = (identifiant, moi, cle_partagee)
        st.session_state["identite"] = resultat
        st.session_state["identite_brute"] = (moi, mot)
        # Retient le prénom affiché (indépendamment du profil facultatif) : sert
        # uniquement à ce que le propriétaire reconnaisse qui est qui dans l'outil
        # d'activation premium - l'identifiant seul est un hash illisible.
        try:
            repository.enregistrer_prenom(identifiant, moi)
        except Exception:
            pass  # ne bloque jamais la connexion pour ça
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

    if not get_shared_api_key() and not get_api_key():
        st.error(
            "L'appli n'est pas encore configurée (aucune clé Gemini disponible). "
            "Réessaie plus tard."
        )
        st.stop()

    st.markdown(
        "📄 **Dépose tes notes de cours** (PDF, photos, captures d'écran)\n\n"
        "🧠 **L'IA te prépare une fiche de synthèse claire** + les notions probables à l'examen\n\n"
        "✅ **Teste-toi avec des quiz adaptés** (avant/après révision, examen blanc chronométré)\n\n"
        "📈 **Suis ta progression** pour arriver serein le jour J"
    )
    st.divider()

    st.write(
        "**Première visite ?** Choisis un prénom et invente un mot de passe.\n\n"
        "**Déjà venu ?** Retape exactement le même prénom et le même mot de passe "
        "pour retrouver ton espace — ce n'est pas une nouvelle inscription, tous tes "
        "cours seront là."
    )

    st.page_link("pages/6_Demo.py", label="Voir un exemple sans rien remplir")

    with st.form("identification_form"):
        nom = st.text_input("Ton prénom", placeholder="Ex : Alice")
        mot = st.text_input(
            "Ton mot de passe",
            type="password",
            help=(
                "Nouveau ici : invente-en un et retiens-le bien. Déjà venu : "
                "retape le même que la dernière fois."
            ),
        )
        ok = st.form_submit_button("Commencer")
        if ok:
            if nom.strip() and mot.strip():
                st.query_params["moi"] = nom.strip()
                st.query_params["mot"] = mot.strip()
                st.rerun()
            else:
                st.error("Les deux champs sont obligatoires.")

    st.page_link("pages/5_Conditions.py", label="Conditions d'utilisation")

    st.caption(
        "Astuce : une fois connecté, tu n'as plus besoin de retaper ça en changeant "
        "d'onglet. Pour revenir plus tard sans tout retaper, mets en favori le lien "
        "personnel affiché sur la page d'accueil."
    )

    st.stop()


def oublier_identite():
    """Efface l'identité mémorisée pour cette visite, pour changer de personne."""
    st.session_state.pop("identite", None)
    st.session_state.pop("identite_brute", None)
    st.query_params.clear()


def lien_personnel_actuel() -> str | None:
    """Lien à mettre en favori pour retrouver son espace (mode partagé uniquement)."""
    brute = st.session_state.get("identite_brute")
    if not brute:
        return None
    from urllib.parse import quote

    prenom, mot = brute
    return f"?moi={quote(prenom)}&mot={quote(mot)}"
