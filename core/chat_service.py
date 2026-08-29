"""Orchestration de la discussion libre sur un cours."""

from core import repository
from core.config import SEUIL_LIMITE_TECHNIQUE_CARACTERES
from core.mistral_client import repondre_chat
from core.prompts import prompt_contexte_chat


def poser_question(cours_id: int, proprietaire: str, question: str) -> str:
    cours = repository.obtenir_cours(cours_id, proprietaire)
    if not cours:
        raise ValueError("Ce cours n'existe pas ou ne t'appartient pas.")

    texte = repository.texte_complet_du_cours(cours_id)
    if not texte.strip():
        raise ValueError(
            "Aucun texte n'a encore été extrait pour ce cours. "
            "Ajoute au moins un document avant de poser une question."
        )

    if len(texte) > SEUIL_LIMITE_TECHNIQUE_CARACTERES:
        raise ValueError(
            "Ce cours est trop volumineux pour que l'IA puisse répondre (il dépasse "
            "sa limite technique). Divise-le en plusieurs cours plus petits (par "
            "chapitre, par exemple)."
        )

    historique = [
        {"role": m["role"], "contenu": m["contenu"]}
        for m in repository.lister_messages_chat(cours_id)
    ]

    contexte = prompt_contexte_chat(cours["nom"], texte)
    reponse = repondre_chat(contexte, historique, question)

    repository.ajouter_message_chat(cours_id, "utilisateur", question)
    repository.ajouter_message_chat(cours_id, "assistant", reponse)
    return reponse
