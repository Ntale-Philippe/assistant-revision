"""Génération des quiz, et calcul du score d'une tentative."""

from core import repository
from core.config import (
    DUREE_EXAMEN_ECRIT_MINUTES,
    DUREE_EXAMEN_MINUTES,
    NB_QUESTIONS_DIAGNOSTIQUE,
    NB_QUESTIONS_ECRIT,
    NB_QUESTIONS_EXAMEN,
    SEUIL_LIMITE_TECHNIQUE_CARACTERES,
)
from core.mistral_client import generer_json
from core.prompts import prompt_correction_ecrite, prompt_quiz, prompt_quiz_ecrit


def _verifier_taille(cours_id: int, proprietaire: str) -> tuple[dict, str, str]:
    """Vérifications communes à tous les types de quiz. Retourne (cours, texte du
    cours, texte des anciens examens)."""
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

    return cours, texte, repository.texte_examens_passes(cours_id)


def generer_quiz(cours_id: int, proprietaire: str, type_quiz: str) -> int:
    """Génère un quiz à choix multiples (diagnostique ou examen_blanc) et le
    sauvegarde. Retourne son id."""
    cours, texte, examens_passes = _verifier_taille(cours_id, proprietaire)

    if type_quiz == "examen_blanc":
        nb_questions = NB_QUESTIONS_EXAMEN
        duree_minutes = DUREE_EXAMEN_MINUTES
    else:
        nb_questions = NB_QUESTIONS_DIAGNOSTIQUE
        duree_minutes = None

    prompt = prompt_quiz(cours["nom"], texte, type_quiz, nb_questions, examens_passes)
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


def generer_quiz_ecrit(cours_id: int, proprietaire: str) -> int:
    """Génère un jeu de questions à réponse écrite (pas de choix multiples) et le
    sauvegarde. Retourne son id."""
    cours, texte, examens_passes = _verifier_taille(cours_id, proprietaire)

    prompt = prompt_quiz_ecrit(cours["nom"], texte, NB_QUESTIONS_ECRIT, examens_passes)
    resultat = generer_json(prompt)
    questions = resultat["questions"]

    quiz_id = repository.creer_quiz(cours_id, "reponse_ecrite", DUREE_EXAMEN_ECRIT_MINUTES)
    for i, q in enumerate(questions):
        repository.ajouter_question(
            quiz_id=quiz_id,
            ordre=i,
            enonce=q["enonce"],
            choix=[],
            bonne_reponse_index=-1,
            type_question="ecrite",
            reponse_modele=q["reponse_modele"],
        )
    return quiz_id


def corriger(questions: list[dict], reponses: list[int]) -> tuple[int, int]:
    """Compare les réponses données aux bonnes réponses (QCM). Retourne (score, score_max)."""
    score = sum(
        1
        for q, r in zip(questions, reponses)
        if r is not None and r == q["bonne_reponse_index"]
    )
    return score, len(questions)


def corriger_ecrit(questions: list[dict], reponses_texte: list[str]) -> tuple[int, int, list[dict]]:
    """Fait corriger par l'IA les réponses écrites d'un coup (une seule requête pour
    toutes les questions, plutôt qu'une par question, pour économiser le quota).
    Retourne (score, score_max, details) où `details` est une liste de
    {"correcte": bool, "commentaire": str} dans l'ordre des questions."""
    paires = [
        {
            "enonce": q["enonce"],
            "reponse_modele": q["reponse_modele"],
            "reponse_etudiant": (reponses_texte[i] or "").strip(),
        }
        for i, q in enumerate(questions)
    ]
    prompt = prompt_correction_ecrite(paires)
    resultat = generer_json(prompt)
    details = resultat["resultats"]
    score = sum(1 for d in details if d.get("correcte"))
    return score, len(questions), details
