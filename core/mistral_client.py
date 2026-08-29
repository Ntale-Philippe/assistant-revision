"""Wrapper autour du SDK Mistral : un seul endroit qui parle à l'API Mistral.

Mistral gère toute la génération de texte de l'appli (synthèse, quiz, chat) — son
plan gratuit est bien plus généreux que celui de Google (pas de plafond bloquant de
20 requêtes/jour, aucune carte bancaire nécessaire). Gemini reste utilisé uniquement
pour lire les images et les PDF scannés (voir core/gemini_client.py), car c'est là
qu'il excelle et que le volume d'appels reste faible.
"""

import json
import time

import streamlit as st
from mistralai.client import Mistral

from core.config import get_mistral_api_key, get_shared_mistral_api_key

MISTRAL_MODEL = "mistral-small-latest"

# Codes/mots-clés d'erreur temporaires : ça vaut le coup de réessayer avant d'abandonner.
CODES_TEMPORAIRES = ("429", "500", "502", "503", "504", "TIMEOUT", "RATE LIMIT", "CAPACITY EXCEEDED")
TENTATIVES_MAX = 3
DELAI_INITIAL_SECONDES = 2
DELAI_TIMEOUT_MS = 60_000


class MistralNonConfigure(Exception):
    """Levée quand aucune clé Mistral n'est configurée (locale ou partagée)."""


def _cle_active() -> str | None:
    """La même clé Mistral sert à tout le monde (pas de clé par visiteur, comme pour
    Gemini) : on préfère la clé partagée (appli en ligne) si elle existe, sinon la
    clé locale (usage solo sur ton PC)."""
    return get_shared_mistral_api_key() or get_mistral_api_key()


@st.cache_resource
def _get_client(api_key: str) -> Mistral:
    if not api_key:
        raise MistralNonConfigure("Clé API Mistral manquante.")
    return Mistral(api_key=api_key, timeout_ms=DELAI_TIMEOUT_MS)


def _client_actif() -> Mistral:
    return _get_client(_cle_active())


def _est_erreur_temporaire(e: Exception) -> bool:
    texte = str(e).upper()
    return any(code in texte for code in CODES_TEMPORAIRES)


def _avec_reessai(appel):
    """Exécute `appel()` en réessayant automatiquement si Mistral répond une erreur
    temporaire (surcharge, limite de débit, délai dépassé). Abandonne immédiatement
    pour toute autre erreur (clé invalide, prompt refusé, etc.)."""
    derniere_erreur = None
    for tentative in range(TENTATIVES_MAX):
        try:
            return appel()
        except Exception as e:
            derniere_erreur = e
            if not _est_erreur_temporaire(e) or tentative == TENTATIVES_MAX - 1:
                raise
            time.sleep(DELAI_INITIAL_SECONDES * (2 ** tentative))
    raise derniere_erreur


def message_utilisateur(erreur: Exception) -> str:
    """Transforme une erreur technique en message compréhensible pour l'utilisateur
    (sans préfixe "Erreur" : à ajouter par l'appelant selon le contexte)."""
    texte = str(erreur)
    if "context length" in texte.lower() or "prompt_too_long" in texte.lower():
        # Le cours dépasse la limite technique de contexte de l'IA (un cours énorme,
        # genre plusieurs centaines de pages) : réessayer ne changera rien, il faut
        # diviser le cours.
        return (
            "ce cours est trop volumineux pour être traité en une seule fois par "
            "l'IA (il dépasse sa limite technique). Divise-le en plusieurs cours "
            "plus petits (par chapitre, par exemple) — réessayer ne suffira pas."
        )
    if _est_erreur_temporaire(erreur):
        return (
            "les serveurs de l'IA sont temporairement surchargés ou mettent trop de "
            "temps à répondre (l'appli a déjà réessayé plusieurs fois automatiquement). "
            "Patiente une minute et réessaie."
        )
    return texte


def generer_json(prompt: str) -> dict:
    """Envoie un prompt texte et récupère une réponse JSON déjà parsée (dict)."""
    client = _client_actif()
    response = _avec_reessai(lambda: client.chat.complete(
        model=MISTRAL_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    ))
    return json.loads(response.choices[0].message.content)


def generer_texte(prompt: str) -> str:
    """Envoie un prompt texte simple et récupère la réponse en texte brut."""
    client = _client_actif()
    response = _avec_reessai(lambda: client.chat.complete(
        model=MISTRAL_MODEL,
        messages=[{"role": "user", "content": prompt}],
    ))
    return response.choices[0].message.content


def repondre_chat(contexte: str, historique: list[dict], nouvelle_question: str) -> str:
    """Répond à une question dans une conversation multi-tours.

    `historique` est une liste de dicts {"role": "utilisateur"|"assistant", "contenu": str}
    déjà échangés avant cette nouvelle question (sans elle)."""
    client = _client_actif()

    messages = [
        {"role": "user", "content": contexte},
        {"role": "assistant", "content": "Compris, je suis prêt à répondre à tes questions sur ce cours."},
    ]
    for message in historique:
        role = "user" if message["role"] == "utilisateur" else "assistant"
        messages.append({"role": role, "content": message["contenu"]})
    messages.append({"role": "user", "content": nouvelle_question})

    response = _avec_reessai(lambda: client.chat.complete(model=MISTRAL_MODEL, messages=messages))
    return response.choices[0].message.content
