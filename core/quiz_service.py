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


def message_resultat(type_quiz: str, score: int, score_max: int, score_precedent: int | None = None) -> str:
    """Message personnalisé après correction, selon le type de quiz (le cadrage
    n'est pas le même avant/après révision, en examen blanc ou à l'écrit) et le
    score obtenu. Purement basé sur des règles (pas d'appel IA) : rapide, fiable,
    et ça évite de consommer du quota pour un simple message d'encouragement.

    `score_precedent` (uniquement pour type_quiz="apres") : le score obtenu au
    quiz diagnostique AVANT révision, pour pouvoir comparer et féliciter la
    progression plutôt qu'annoncer juste un pourcentage brut."""
    pourcentage = round(100 * score / score_max) if score_max else 0

    if type_quiz == "avant":
        if pourcentage >= 70:
            return f"Tu maîtrises déjà bien ce cours ({pourcentage}%) ! Révise quand même les points ratés pour viser le sans-faute."
        if pourcentage >= 40:
            return (
                f"Bon diagnostic ({pourcentage}%) : tu as des bases, mais plusieurs points à "
                "consolider avant l'examen. Utilise ta fiche de synthèse pour cibler tes lacunes."
            )
        return (
            f"C'est normal de ne pas tout savoir avant de réviser ({pourcentage}%) — c'est "
            "justement le but de ce quiz : repérer où concentrer tes efforts. Fonce sur la "
            "fiche de synthèse !"
        )

    if type_quiz == "apres":
        if score_precedent is not None:
            delta = score - score_precedent
            if delta > 0:
                return (
                    f"Bravo, tu progresses : {score_precedent} → {score} bonnes réponses "
                    f"({pourcentage}%) ! Ta révision a payé."
                )
            if delta == 0:
                return (
                    f"Même score qu'avant révision ({pourcentage}%) — relis ta fiche de "
                    "synthèse sur les points ratés avant de retenter."
                )
            return (
                f"Ton score a un peu baissé par rapport à avant révision ({pourcentage}%) — "
                "pas de panique, ça arrive (fatigue, stress). Relis calmement ta fiche avant "
                "de reprendre."
            )
        if pourcentage >= 70:
            return f"Bon score après révision ({pourcentage}%) !"
        return f"Score après révision : {pourcentage}%. Continue à réviser les points faibles."

    if type_quiz == "examen_blanc":
        if pourcentage >= 80:
            return f"Excellent ({pourcentage}%) : tu es prêt pour l'examen. Garde ce rythme de révision."
        if pourcentage >= 50:
            return (
                f"Score correct ({pourcentage}%), mais encore du travail avant d'être serein "
                "le jour J. Repère les questions ratées et retravaille ces points précis."
            )
        return (
            f"Ce résultat ({pourcentage}%) montre qu'il reste du travail avant l'examen — "
            "mieux vaut le découvrir maintenant qu'en salle d'examen. Reprends ta fiche de "
            "synthèse en profondeur."
        )

    if type_quiz == "ecrit":
        if pourcentage >= 80:
            return (
                f"Très bonnes réponses rédigées ({pourcentage}%) : tu sais formuler tes "
                "connaissances clairement, pas seulement les reconnaître."
            )
        if pourcentage >= 50:
            return (
                f"Correct dans l'ensemble ({pourcentage}%), mais travaille la précision de ta "
                "rédaction — relis les réponses modèles pour voir ce qui manquait."
            )
        return (
            f"Rédiger de mémoire est plus dur que choisir une réponse ({pourcentage}%) — normal "
            "si c'est nouveau pour toi. Relis les réponses modèles pour t'entraîner."
        )

    return f"Score : {pourcentage}%."
