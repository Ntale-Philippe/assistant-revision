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
NB_QUESTIONS_ECRIT = 5
DUREE_EXAMEN_ECRIT_MINUTES = 15

# Accès premium (3$ pour l'accès complet jusqu'à la fin du semestre, activé
# manuellement par le propriétaire après un paiement reçu hors appli).
DUREE_PREMIUM_JOURS = 120
PRIX_PREMIUM = 3.0
DEVISE_PREMIUM = "USD"
NB_QUESTIONS_CHAT_GRATUIT = 2

# Seuils pour les gros cours (beaucoup de documents, ou documents très longs).
# Important : on envoie TOUJOURS tout le texte en un seul appel à l'IA (jamais
# découpé en plusieurs appels), car le plan gratuit de Google limite le nombre de
# *requêtes* par jour (pas la taille d'une requête) — découper en morceaux
# consommerait plusieurs fois ce quota très restreint pour une seule génération.
SEUIL_AVERTISSEMENT_CARACTERES = 30_000
# Au-delà de ce seuil, le cours est si volumineux (l'équivalent d'un manuel entier)
# qu'on recommande activement de le diviser en plusieurs cours (par chapitre par
# exemple), pour ne pas risquer d'épuiser le quota gratuit du jour à lui seul.
SEUIL_ENORME_CARACTERES = 300_000
# Au-delà de ce seuil, la génération ÉCHOUERA quasi certainement : ça dépasse la
# limite technique de contexte du modèle Mistral utilisé (mesuré empiriquement :
# ~984 000 caractères de contenu ont produit un prompt de 273 940 tokens contre une
# limite de 262 144 — marge de sécurité prise ici).
SEUIL_LIMITE_TECHNIQUE_CARACTERES = 850_000

# Extensions de fichiers acceptées à l'upload (V1 : texte + images/PDF, audio prévu pour plus tard)
# Séparées en deux groupes : sur Android, mélanger images et autres fichiers dans une
# même zone de dépôt fait parfois disparaître l'option "Fichiers" du sélecteur (bug
# connu d'Android 14/15), ne laissant que l'appareil photo/galerie. Deux zones séparées
# évitent le problème.
EXTENSIONS_DOCUMENTS = ["pdf", "txt", "pptx", "docx", "xlsx", "csv"]
EXTENSIONS_IMAGES = ["png", "jpg", "jpeg"]

# Liste de pays pour le profil facultatif (auto-déclaré, pas de géolocalisation
# technique) : sert uniquement à la répartition géographique dans les statistiques
# avancées. Pays francophones d'Afrique en tête (public principal de l'appli),
# suivis d'une liste internationale large.
LISTE_PAYS = [
    "", "République démocratique du Congo", "Congo-Brazzaville", "Cameroun", "Côte d'Ivoire",
    "Sénégal", "Mali", "Burkina Faso", "Bénin", "Togo", "Niger", "Guinée", "Rwanda", "Burundi",
    "Gabon", "Tchad", "République centrafricaine", "Madagascar", "Maroc", "Algérie", "Tunisie",
    "Belgique", "France", "Suisse", "Canada",
    "Nigéria", "Kenya", "Ghana", "Afrique du Sud", "Égypte", "Éthiopie", "Ouganda", "Tanzanie",
    "Zambie", "Zimbabwe", "Angola", "Mozambique",
    "États-Unis", "Royaume-Uni", "Allemagne", "Espagne", "Italie", "Portugal",
    "Chine", "Inde", "Brésil", "Autre",
]


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


def get_mistral_api_key() -> str | None:
    """Clé Mistral pour l'usage solo, en local sur ton PC (secrets.toml local)."""
    try:
        return st.secrets["MISTRAL_API_KEY"]
    except Exception:
        return None


def get_shared_mistral_api_key() -> str | None:
    """Clé Mistral utilisée pour TOUS les visiteurs de l'appli hébergée. Mistral gère
    la synthèse, les quiz et le chat (texte) : quota gratuit bien plus généreux que
    Gemini, et aucune carte bancaire nécessaire."""
    try:
        return st.secrets["SHARED_MISTRAL_API_KEY"]
    except Exception:
        return None


def get_admin_password() -> str | None:
    """Mot de passe qui débloque les statistiques avancées (page Statistiques),
    réservées au propriétaire de l'appli — distinct de son prénom/mot de passe
    habituel, pour que ça marche pareil qu'il soit en mode solo ou partagé."""
    try:
        return st.secrets["ADMIN_PASSWORD"]
    except Exception:
        return None


def ensure_dirs():
    """Crée les dossiers de données s'ils n'existent pas encore."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
