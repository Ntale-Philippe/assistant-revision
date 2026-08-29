"""Génération des quiz, et calcul du score d'une tentative."""

from core import repository
from core.config import (
    DUREE_EXAMEN_MINUTES,
    NB_QUESTIONS_DIAGNOSTIQUE,
    NB_QUESTIONS_EXAMEN,
    SEUIL_LIMITE_TECHNIQUE_CARACTERES,
)
from core.mistral_client import generer_json
from core.prompts import prompt_quiz


def generer_quiz(cours_id: int, proprietaire: str, type_quiz: str) -> int:
    """Génère un quiz (diagnostique ou examen_blanc) et le sauvegarde. Retourne son id."""
    cours = repository.obtenir_cours(cours_id, proprietaire)
    if not cours:
        raise ValueError("Ce cours n'existe pas ou ne t'appartient pas.")

    texte = repository.texte_complet_du_cours(cours_id)

    if not texte.strip():
        raise ValueError(
            "Aucun texte n'a encore été extrait pour ce cours. "
            "Ajoute au moins un document avant de générer un quiz."
        )

    if len(texte) > SEUIL_LIMITE_TECHNIQUE_CARACTERES:
        raise ValueError(
            "Ce cours est trop volumineux pour être traité en une seule fois par "
            "l'IA (il dépasse sa limite technique). Divise-le en plusieurs cours "
            "plus petits (par chapitre, par exemple) — réessayer ne suffira pas."
        )

    if type_quiz == "examen_blanc":
        nb_questions = NB_QUESTIONS_EXAMEN
        duree_minutes = DUREE_EXAMEN_MINUTES
    else:
        nb_questions = NB_QUESTIONS_DIAGNOSTIQUE
        duree_minutes = None

    prompt = prompt_quiz(cours["nom"], texte, type_quiz, nb_questions)
    resultat = generer_json(prompt)
    questions = resultat["questions"]

    quiz_id = repository.creer_quiz(cours_id, type_quiz, duree_minutes)
    for i, q in enumerate(questions):
        repository.ajouter_question(
            quiz_id=quiz_id,
            ordre=i,
            enonce=q["enonce"],
            choix=q["choix"],
            bonne_reponse_index=q["bonne_reponse_index"],
            explication=q.get("explication", ""),
        )
    return quiz_id


def corriger(questions: list[dict], reponses: list[int]) -> tuple[int, int]:
    """Compare les réponses données aux bonnes réponses. Retourne (score, score_max)."""
    score = sum(
        1
        for q, r in zip(questions, reponses)
        if r is not None and r == q["bonne_reponse_index"]
    )
    return score, len(questions)
