"""Wrapper autour du SDK google-genai : un seul endroit qui parle à l'API Gemini.

Chaque appel reçoit la clé API de la personne qui l'utilise (elle peut être différente
pour chaque visiteur de l'appli quand elle est partagée entre plusieurs collègues).
"""

import time

import streamlit as st
from google import genai
from google.genai import types

from core.config import GEMINI_MODEL

# Codes d'erreur temporaires côté Google : ça vaut le coup de réessayer avant
# d'abandonner (surcharge passagère, quota atteint sur une courte fenêtre...).
CODES_TEMPORAIRES = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "TIMEOUT", "DEADLINE_EXCEEDED")
TENTATIVES_MAX = 3
DELAI_INITIAL_SECONDES = 2

# Temps maximum qu'on laisse à UN appel à Google avant d'abandonner (en millisecondes).
# Sans ça, un appel qui ne répond jamais (connexion qui traîne) bloque l'appli
# indéfiniment : l'utilisateur voit tourner le spinner sans fin, sans même un message
# d'erreur pour comprendre ce qui se passe.
DELAI_TIMEOUT_MS = 60_000

# Après un échec, on empêche de recliquer tout de suite : cliquer 10 fois d'affilée
# sur "Générer" ne fait qu'aggraver un ralentissement passager côté Google (chaque
# clic relance nos propres tentatives automatiques par-dessus).
DELAI_ENTRE_ESSAIS_SECONDES = 20


def peut_reessayer(cle: str) -> tuple[bool, int]:
    """Vérifie si assez de temps s'est écoulé depuis le dernier échec pour cette
    action (ex: "synthese_12"). Retourne (peut_reessayer, secondes_restantes)."""
    dernier_echec = st.session_state.get(f"echec_ia_{cle}")
    if dernier_echec is None:
        return True, 0
    restant = int(DELAI_ENTRE_ESSAIS_SECONDES - (time.time() - dernier_echec))
    return (restant <= 0), max(restant, 0)


def signaler_echec(cle: str):
    st.session_state[f"echec_ia_{cle}"] = time.time()


def signaler_succes(cle: str):
    st.session_state.pop(f"echec_ia_{cle}", None)


class GeminiNonConfigure(Exception):
    """Levée quand la clé API n'est pas configurée."""


@st.cache_resource
def _get_client(api_key: str) -> genai.Client:
    # st.cache_resource garde un client par valeur de clé différente : chaque personne
    # a donc son propre client Gemini, sans jamais mélanger les clés.
    if not api_key:
        raise GeminiNonConfigure("Clé API Gemini manquante.")
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=DELAI_TIMEOUT_MS),
    )


def _est_erreur_temporaire(e: Exception) -> bool:
    # httpx (utilisé sous le capot par le SDK Gemini) lève des classes comme
    # ReadTimeout/ConnectTimeout dont le message est "The read operation timed out"
    # (avec un espace) : ne contient PAS le mot "TIMEOUT" cherché plus bas — même
    # bug que celui trouvé et corrigé côté Mistral, présent ici aussi pour la
    # lecture des images/PDF scannés (lire_image/lire_pdf).
    if "TIMEOUT" in type(e).__name__.upper():
        return True
    texte = str(e).upper()
    return any(code in texte for code in CODES_TEMPORAIRES)


def _avec_reessai(appel):
    """Exécute `appel()` en réessayant automatiquement si Gemini répond une erreur
    temporaire (surcharge, quota momentané, délai dépassé). Abandonne immédiatement
    pour toute autre erreur (clé invalide, prompt refusé, etc.) : réessayer ne
    servirait à rien."""
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
    if "PERDAY" in texte.upper().replace(" ", ""):
        # Quota GRATUIT *quotidien* épuisé : dire "réessaie dans une minute" serait
        # trompeur ici, ça ne repartira pas avant le renouvellement du quota.
        return (
            "le quota gratuit quotidien de l'IA de Google est épuisé pour aujourd'hui "
            "(le plan gratuit de Google est très limité). Réessaie plus tard dans la "
            "journée, ou demain si ça persiste."
        )
    if _est_erreur_temporaire(erreur):
        return (
            "les serveurs de Google sont temporairement surchargés ou mettent trop "
            "de temps à répondre (l'appli a déjà réessayé plusieurs fois "
            "automatiquement). Patiente une minute et réessaie."
        )
    return texte


def lire_image(image_bytes: bytes, mime_type: str, prompt: str, api_key: str) -> str:
    """Envoie une image + un prompt de transcription, récupère le texte transcrit."""
    client = _get_client(api_key)
    response = _avec_reessai(lambda: client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt,
        ],
    ))
    return response.text


def lire_pdf(pdf_bytes: bytes, prompt: str, api_key: str) -> str:
    """Envoie un PDF (probablement scanné) + un prompt, récupère le texte transcrit."""
    client = _get_client(api_key)
    response = _avec_reessai(lambda: client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            prompt,
        ],
    ))
    return response.text
