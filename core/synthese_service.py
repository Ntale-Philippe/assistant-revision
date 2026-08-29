"""Orchestration : texte des documents d'un cours -> IA -> fiche de synthèse sauvegardée."""

from core import repository
from core.condensation_service import texte_pret_pour_ia
from core.gemini_client import generer_json
from core.prompts import prompt_synthese


def generer_et_sauver_synthese(cours_id: int, proprietaire: str, api_key: str) -> dict:
    cours = repository.obtenir_cours(cours_id, proprietaire)
    if not cours:
        raise ValueError("Ce cours n'existe pas ou ne t'appartient pas.")

    texte = repository.texte_complet_du_cours(cours_id)

    if not texte.strip():
        raise ValueError(
            "Aucun texte n'a encore été extrait pour ce cours. "
            "Ajoute au moins un document et attends la fin de son extraction."
        )

    texte = texte_pret_pour_ia(texte, api_key)
    prompt = prompt_synthese(cours["nom"], texte)
    synthese = generer_json(prompt, api_key)
    repository.sauver_synthese(cours_id, synthese)
    return synthese
