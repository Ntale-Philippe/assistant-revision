"""Orchestration : texte des documents d'un cours -> IA -> fiche de synthèse sauvegardée."""

from core import repository
from core.config import SEUIL_LIMITE_TECHNIQUE_CARACTERES
from core.mistral_client import generer_json
from core.prompts import prompt_synthese


def _en_markdown(valeur) -> str:
    """L'IA répond parfois avec une liste au lieu d'une chaîne de texte pour une
    section (ex: fun_facts) : on la remet en forme en liste à puces Markdown plutôt
    que de planter à l'affichage."""
    if isinstance(valeur, list):
        return "\n".join(f"- {item}" for item in valeur)
    return str(valeur)


def generer_et_sauver_synthese(cours_id: int, proprietaire: str) -> dict:
    cours = repository.obtenir_cours(cours_id, proprietaire)
    if not cours:
        raise ValueError("Ce cours n'existe pas ou ne t'appartient pas.")

    texte = repository.texte_complet_du_cours(cours_id)

    if not texte.strip():
        raise ValueError(
            "Aucun texte n'a encore été extrait pour ce cours. "
            "Ajoute au moins un document et attends la fin de son extraction."
        )

    if len(texte) > SEUIL_LIMITE_TECHNIQUE_CARACTERES:
        # Vérifié avant d'appeler l'IA : au-delà de ce seuil, l'appel échoue de toute
        # façon (limite de contexte du modèle) — parfois vite (erreur nette), parfois
        # après une longue attente (timeout). Autant échouer tout de suite avec un
        # message clair plutôt que de faire attendre l'utilisateur pour rien.
        raise ValueError(
            "Ce cours est trop volumineux pour être traité en une seule fois par "
            "l'IA (il dépasse sa limite technique). Divise-le en plusieurs cours "
            "plus petits (par chapitre, par exemple) — réessayer ne suffira pas."
        )

    prompt = prompt_synthese(cours["nom"], texte)
    # Borne la longueur de la réponse : sans ça, la section "synthese" (ouverte, pas
    # de nombre fixe comme les questions de quiz) peut partir sur une réponse très
    # longue pour un gros cours, ce qui prend plus de temps et augmente le risque de
    # timeout — c'est précisément ce qui faisait échouer la synthèse alors que le
    # quiz (toujours borné à un nombre fixe de questions) réussissait sur le même cours.
    synthese = generer_json(prompt, max_tokens=6000)
    synthese = {cle: _en_markdown(valeur) for cle, valeur in synthese.items()}
    repository.sauver_synthese(cours_id, synthese)
    return synthese
