"""Configuration centrale de l'application : clé API, chemins, constantes."""

from pathlib import Path

import streamlit as st

# Dossiers du projet
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "app.db"
UPLOADS_DIR = DATA_DIR / "uploads"

# Modèle Gemini utilisé (rapide et gratuit dans le tier gratuit de Google AI Studio)
GEMINI_MODEL = "gemini-3.6-flash"

# Nombre de questions par type de quiz
NB_QUESTIONS_DIAGNOSTIQUE = 8
NB_QUESTIONS_EXAMEN = 15
DUREE_EXAMEN_MINUTES = 20

# Extensions de fichiers acceptées à l'upload (V1 : texte + images/PDF, audio prévu pour plus tard)
# Séparées en deux groupes : sur Android, mélanger images et autres fichiers dans une
# même zone de dépôt fait parfois disparaître l'option "Fichiers" du sélecteur (bug
# connu d'Android 14/15), ne laissant que l'appareil photo/galerie. Deux zones séparées
# évitent le problème.
EXTENSIONS_DOCUMENTS = ["pdf", "txt", "pptx", "docx", "xlsx", "csv"]
EXTENSIONS_IMAGES = ["png", "jpg", "jpeg"]
EXTENSIONS_ACCEPTEES = EXTENSIONS_DOCUMENTS + EXTENSIONS_IMAGES


def get_api_key() -> str | None:
    """Lit la clé API Gemini depuis .streamlit/secrets.toml. Retourne None si absente.

    Sur l'appli hébergée (sans secrets.toml, volontairement), Streamlit peut lever
    différents types d'erreurs selon la version : on les attrape toutes largement,
    l'absence de clé n'est pas une erreur ici, juste une info ("mode partagé")."""
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return None


def ensure_dirs():
    """Crée les dossiers de données s'ils n'existent pas encore."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
