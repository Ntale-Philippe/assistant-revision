"""Tous les prompts envoyés à Gemini, centralisés ici pour être faciles à ajuster."""

PROMPT_OCR_IMAGE = """Transcris fidèlement tout le texte visible sur cette image
(notes manuscrites, texte imprimé, légendes, titres). Si un schéma, un graphique
ou un dessin est présent, décris brièvement et clairement ce qu'il représente
et les éléments qu'il contient. Réponds uniquement avec le texte transcrit/décrit,
en français, sans commentaire ni introduction."""

PROMPT_OCR_PDF_SCANNE = """Ce PDF est probablement un scan (notes, slides ou article
photographié/scanné). Transcris fidèlement tout le texte qu'il contient, page par
page si utile. Décris brièvement les schémas ou graphiques présents.
Réponds uniquement avec le texte transcrit, en français."""


def prompt_synthese(nom_cours: str, texte: str) -> str:
    return f"""Tu es un excellent tuteur universitaire en biologie, pédagogue et précis.
Voici tout le contenu extrait des documents du cours "{nom_cours}" :

---
{texte}
---

À partir de ce contenu, génère une fiche de révision structurée avec exactement ces
5 sections (réponds en français, dans un style clair pour un étudiant) :

1. "synthese" : un résumé structuré et complet du cours (les points clés, organisés
   logiquement, en Markdown avec des titres ## et des listes à puces).
2. "contexte" : pourquoi ce sujet est important en biologie (lien avec d'autres notions,
   applications médicales/scientifiques, pourquoi un biologiste doit le comprendre).
3. "notions_examen" : les passages, définitions ou mécanismes les plus susceptibles de
   tomber à l'examen, avec une courte justification pour chacun (liste à puces).
4. "a_retenir" : les notions fondamentales à retenir "pour la vie", au-delà de l'examen
   (liste à puces, allant à l'essentiel).
5. "fun_facts" : 3 à 5 faits surprenants ou anecdotes liés au sujet, pour rendre le
   cours mémorable.

Réponds uniquement avec un objet JSON valide contenant ces 5 clés (chaînes de texte
en Markdown), sans texte avant ou après."""


def prompt_quiz(nom_cours: str, texte: str, type_quiz: str, nb_questions: int) -> str:
    if type_quiz == "examen_blanc":
        consigne_difficulte = (
            "Difficulté élevée, type examen universitaire : inclus des questions de mise "
            "en situation, d'application et de compréhension fine, pas seulement du pur "
            "par-cœur. Les mauvaises réponses (distracteurs) doivent être plausibles."
        )
    else:
        consigne_difficulte = (
            "Difficulté facile à moyenne : l'objectif est d'évaluer les connaissances de "
            "base et de repérer les lacunes, pas de piéger l'étudiant."
        )

    return f"""Tu es un professeur de biologie qui prépare un quiz à choix multiples (QCM)
pour le cours "{nom_cours}", à partir du contenu suivant :

---
{texte}
---

Génère exactement {nb_questions} questions à choix multiples couvrant l'ensemble du
contenu (varie les notions abordées, ne te concentre pas sur un seul passage).
{consigne_difficulte}

Pour chaque question, fournis :
- "enonce" : l'énoncé de la question
- "choix" : une liste de exactement 4 propositions de réponse
- "bonne_reponse_index" : l'index (0 à 3) de la bonne réponse dans "choix"
- "explication" : une courte explication de pourquoi c'est la bonne réponse

Réponds uniquement avec un objet JSON valide contenant une clé "questions" qui est
une liste de {nb_questions} objets avec ces 4 clés. Pas de texte avant ou après, en français."""
