"""Wrapper autour du SDK google-genai : un seul endroit qui parle à l'API Gemini.

Chaque appel reçoit la clé API de la personne qui l'utilise (elle peut être différente
pour chaque visiteur de l'appli quand elle est partagée entre plusieurs collègues).
"""

import json
import time

import streamlit as st
from google import genai
from google.genai import types

from core.config import GEMINI_MODEL

# Codes d'erreur temporaires côté Google : ça vaut le coup de réessayer avant
# d'abandonner (surcharge passagère, quota atteint sur une courte fenêtre...).
CODES_TEMPORAIRES = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")
TENTATIVES_MAX = 3
DELAI_INITIAL_SECONDES = 2

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
    return genai.Client(api_key=api_key)


def _avec_reessai(appel):
    """Exécute `appel()` en réessayant automatiquement si Gemini répond une erreur
    temporaire (surcharge, quota momentané). Abandonne immédiatement pour toute
    autre erreur (clé invalide, prompt refusé, etc.) : réessayer ne servirait à rien."""
    derniere_erreur = None
    for tentative in range(TENTATIVES_MAX):
        try:
            return appel()
        except Exception as e:
            derniere_erreur = e
            est_temporaire = any(code in str(e) for code in CODES_TEMPORAIRES)
            if not est_temporaire or tentative == TENTATIVES_MAX - 1:
                raise
            time.sleep(DELAI_INITIAL_SECONDES * (2 ** tentative))
    raise derniere_erreur


def message_utilisateur(erreur: Exception) -> str:
    """Transforme une erreur technique en message compréhensible pour l'utilisateur
    (sans préfixe "Erreur" : à ajouter par l'appelant selon le contexte)."""
    texte = str(erreur)
    if any(code in texte for code in CODES_TEMPORAIRES):
        return (
            "les serveurs de Google sont temporairement surchargés (l'appli a déjà "
            "réessayé plusieurs fois automatiquement). Patiente une minute et réessaie."
        )
    return texte


def generer_json(prompt: str, api_key: str) -> dict:
    """Envoie un prompt texte et récupère une réponse JSON déjà parsée (dict)."""
    client = _get_client(api_key)
    response = _avec_reessai(lambda: client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    ))
    return json.loads(response.text)


def generer_texte(prompt: str, api_key: str) -> str:
    """Envoie un prompt texte simple et récupère la réponse en texte brut."""
    client = _get_client(api_key)
    response = _avec_reessai(lambda: client.models.generate_content(model=GEMINI_MODEL, contents=[prompt]))
    return response.text


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


def repondre_chat(contexte: str, historique: list[dict], nouvelle_question: str, api_key: str) -> str:
    """Répond à une question dans une conversation multi-tours.

    `historique` est une liste de dicts {"role": "utilisateur"|"assistant", "contenu": str}
    déjà échangés avant cette nouvelle question (sans elle)."""
    client = _get_client(api_key)

    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=contexte)]),
        types.Content(
            role="model",
            parts=[types.Part.from_text(text="Compris, je suis prêt à répondre à tes questions sur ce cours.")],
        ),
    ]
    for message in historique:
        role = "user" if message["role"] == "utilisateur" else "model"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=message["contenu"])]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=nouvelle_question)]))

    response = _avec_reessai(lambda: client.models.generate_content(model=GEMINI_MODEL, contents=contents))
    return response.text
