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

# Identifiant réservé au cours de démonstration publique (aucune inscription requise).
IDENTIFIANT_DEMO = "demo-public"

# Nombre de questions par type de quiz
NB_QUESTIONS_DIAGNOSTIQUE = 8
NB_QUESTIONS_EXAMEN = 15
DUREE_EXAMEN_MINUTES = 20

# Seuils pour les gros cours (beaucoup de documents, ou documents très longs) :
# au-delà de SEUIL_AVERTISSEMENT, on prévient juste l'utilisateur que ça va prendre
# plus de temps. Au-delà de SEUIL_CONDENSATION (plus gros), le texte est condensé en
# plusieurs étapes avant d'être envoyé à l'IA, pour rester rapide et éviter de se
# heurter aux limites gratuites de Google avec un message trop volumineux.
SEUIL_AVERTISSEMENT_CARACTERES = 30_000
SEUIL_CONDENSATION_CARACTERES = 60_000
TAILLE_MORCEAU_CONDENSATION = 25_000

# Extensions de fichiers acceptées à l'upload (V1 : texte + images/PDF, audio prévu pour plus tard)
# Séparées en deux groupes : sur Android, mélanger images et autres fichiers dans une
# même zone de dépôt fait parfois disparaître l'option "Fichiers" du sélecteur (bug
# connu d'Android 14/15), ne laissant que l'appareil photo/galerie. Deux zones séparées
# évitent le problème.
EXTENSIONS_DOCUMENTS = ["pdf", "txt", "pptx", "docx", "xlsx", "csv"]
EXTENSIONS_IMAGES = ["png", "jpg", "jpeg"]


def get_api_key() -> str | None:
    """Clé Gemini pour l'usage solo, en local sur ton PC (secrets.toml local).
    Ne jamais mettre cette clé précise dans les secrets de l'appli hébergée : ce
    serait ouvrir un accès "solo" instantané à n'importe quel visiteur anonyme."""
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return None


def get_shared_api_key() -> str | None:
    """Clé Gemini utilisée pour TOUS les visiteurs identifiés (prénom + mot de passe)
    de l'appli hébergée : personne n'a besoin de créer sa propre clé. C'est celle-ci
    qu'il faut configurer dans les secrets de l'appli en ligne."""
    try:
        return st.secrets["SHARED_GEMINI_API_KEY"]
    except Exception:
        return None


def ensure_dirs():
    """Crée les dossiers de données s'ils n'existent pas encore."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
