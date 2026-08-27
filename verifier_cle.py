"""Petit script pour vérifier que ta clé API Gemini fonctionne bien.

Lance-le avec :
    ".venv/Scripts/python.exe" verifier_cle.py
"""

import sys
import tomllib
from pathlib import Path

from google import genai

# Sur certains terminaux Windows, la sortie standard ne sait pas afficher les emojis
# par défaut : on force l'encodage UTF-8 pour éviter un crash à l'affichage.
sys.stdout.reconfigure(encoding="utf-8")

SECRETS_PATH = Path(__file__).parent / ".streamlit" / "secrets.toml"


def main():
    if not SECRETS_PATH.exists():
        print("Le fichier .streamlit/secrets.toml n'existe pas.")
        return

    with open(SECRETS_PATH, "rb") as f:
        secrets = tomllib.load(f)

    api_key = secrets.get("GEMINI_API_KEY", "")
    if not api_key or api_key == "colle-ta-cle-ici":
        print("Tu n'as pas encore mis ta vraie clé API dans .streamlit/secrets.toml.")
        return

    print("Test de connexion à Gemini...")
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=["Dis simplement 'Bonjour, ça fonctionne !' en français."],
        )
        print("Ça marche. Réponse de Gemini :")
        print(response.text)
    except Exception as e:
        print(f"Erreur lors de l'appel à Gemini : {e}")


if __name__ == "__main__":
    main()
