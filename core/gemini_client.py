"""Wrapper autour du SDK google-genai : un seul endroit qui parle à l'API Gemini.

Chaque appel reçoit la clé API de la personne qui l'utilise (elle peut être différente
pour chaque visiteur de l'appli quand elle est partagée entre plusieurs collègues).
"""

import json

import streamlit as st
from google import genai
from google.genai import types

from core.config import GEMINI_MODEL


class GeminiNonConfigure(Exception):
    """Levée quand la clé API n'est pas configurée."""


@st.cache_resource
def _get_client(api_key: str) -> genai.Client:
    # st.cache_resource garde un client par valeur de clé différente : chaque personne
    # a donc son propre client Gemini, sans jamais mélanger les clés.
    if not api_key:
        raise GeminiNonConfigure("Clé API Gemini manquante.")
    return genai.Client(api_key=api_key)


def generer_json(prompt: str, api_key: str) -> dict:
    """Envoie un prompt texte et récupère une réponse JSON déjà parsée (dict)."""
    client = _get_client(api_key)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    return json.loads(response.text)


def generer_texte(prompt: str, api_key: str) -> str:
    """Envoie un prompt texte simple et récupère la réponse en texte brut."""
    client = _get_client(api_key)
    response = client.models.generate_content(model=GEMINI_MODEL, contents=[prompt])
    return response.text


def lire_image(image_bytes: bytes, mime_type: str, prompt: str, api_key: str) -> str:
    """Envoie une image + un prompt de transcription, récupère le texte transcrit."""
    client = _get_client(api_key)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt,
        ],
    )
    return response.text


def lire_pdf(pdf_bytes: bytes, prompt: str, api_key: str) -> str:
    """Envoie un PDF (probablement scanné) + un prompt, récupère le texte transcrit."""
    client = _get_client(api_key)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            prompt,
        ],
    )
    return response.text
