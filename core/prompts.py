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


def _bloc_examens_passes(examens_passes: str, but: str) -> str:
    """Bloc optionnel inséré dans un prompt quand l'étudiant a déposé d'anciens
    examens de ce cours : `but` précise comment s'en servir (adapté selon qu'on
    génère la synthèse ou un quiz)."""
    if not examens_passes.strip():
        return ""
    return f"""

Voici aussi d'anciens examens de ce cours, déposés par l'étudiant comme référence :
---
{examens_passes}
---
Ce sont de VRAIS examens déjà donnés dans ce cours : {but}"""


def prompt_synthese(nom_cours: str, texte: str, examens_passes: str = "", profil: dict | None = None) -> str:
    bloc_examens = _bloc_examens_passes(
        examens_passes,
        "utilise-les EN PRIORITÉ pour la section \"notions_examen\" — base-toi sur les "
        "notions et questions qui reviennent réellement dans ces examens plutôt que sur "
        "une estimation générale, chaque fois que c'est possible.",
    )

    # .get(clé, "") ne suffit pas ici : la ligne existe dans profils dès la connexion
    # (prénom auto-enregistré), donc la clé est présente mais peut valoir None si
    # l'étudiant n'a jamais rempli "Personnalise l'appli" - `.strip()` sur None plante.
    faculte = ((profil or {}).get("faculte") or "").strip()
    reve = ((profil or {}).get("reve") or "").strip()
    if faculte or reve:
        elements = []
        if faculte:
            elements.append(f'étudie en "{faculte}"')
        if reve:
            elements.append(f'rêve de "{reve}" dans 20 ans')
        consigne_a_retenir = (
            f"""cet étudiant {" et ".join(elements)}. Relie explicitement les notions
   fondamentales de CE cours précis à cet objectif personnel : montre concrètement
   comment ce sujet va l'aider dans sa filière et/ou son rêve, pas des généralités qui
   vaudraient pour n'importe quel étudiant (liste à puces, **5 à 6 éléments maximum**,
   chaque élément en une seule phrase courte — reste lisible sur petit écran de
   téléphone). Ton chaleureux et encourageant, avec quelques emojis pertinents (sans
   en abuser)."""
        )
    else:
        consigne_a_retenir = (
            """les notions fondamentales à retenir "pour la vie", au-delà de l'examen
   (liste à puces, **5 à 6 éléments maximum**, chaque élément en une seule phrase
   courte — reste lisible sur petit écran de téléphone). Ton chaleureux et
   encourageant, avec quelques emojis pertinents (sans en abuser)."""
        )

    return f"""Tu es un excellent tuteur universitaire, pédagogue et précis, capable
d'enseigner n'importe quelle discipline (sciences, droit, lettres, économie, ingénierie...).
Voici tout le contenu extrait des documents du cours "{nom_cours}" :

---
{texte}
---{bloc_examens}

À partir de ce contenu, génère une fiche de révision structurée avec exactement ces
5 sections (réponds en français, dans un style clair pour un étudiant) :

1. "synthese" : un résumé structuré des points clés du cours (organisés logiquement,
   en Markdown avec des titres ## et des listes à puces). Reste synthétique et va à
   l'essentiel même si le cours est volumineux : privilégie les points les plus
   importants plutôt qu'une retranscription exhaustive (quelques centaines de mots
   suffisent, jamais plus d'environ 1000 mots).
2. "contexte" : pourquoi ce sujet est important dans cette discipline (lien avec
   d'autres notions du cursus, applications concrètes, pourquoi un étudiant de cette
   filière doit le maîtriser). Quelques phrases suffisent.
3. "notions_examen" : les passages, définitions ou raisonnements les plus susceptibles
   de tomber à l'examen, avec une courte justification pour chacun (liste à puces,
   **5 à 6 éléments maximum**, chaque élément en une seule phrase courte — reste
   lisible sur petit écran de téléphone).
4. "a_retenir" : {consigne_a_retenir}
5. "fun_facts" : 3 à 5 anecdotes ou faits marquants liés au sujet, pour rendre le
   cours mémorable. Ton chaleureux et enjoué, avec quelques emojis pertinents (sans
   en abuser).

Réponds uniquement avec un objet JSON valide contenant ces 5 clés (chaînes de texte
en Markdown), sans texte avant ou après."""


def prompt_contexte_chat(nom_cours: str, texte: str) -> str:
    return f"""Tu es un tuteur universitaire qui aide un étudiant à réviser le cours
"{nom_cours}". Réponds à ses questions uniquement en te basant sur le contenu du cours
ci-dessous, de façon claire, pédagogique et concise, en français. Si une question
sort du cadre de ce contenu, dis-le simplement plutôt que d'inventer une réponse.

--- Contenu du cours ---
{texte}
--- Fin du contenu ---

Tu es prêt à répondre à ses questions."""


def prompt_quiz(nom_cours: str, texte: str, type_quiz: str, nb_questions: int,
                 examens_passes: str = "") -> str:
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

    bloc_examens = _bloc_examens_passes(
        examens_passes,
        "inspire-toi de leur style, de leurs notions abordées et de leur niveau de "
        "difficulté pour composer ce quiz, en plus du contenu du cours ci-dessus.",
    )

    return f"""Tu es un professeur universitaire qui prépare un quiz à choix multiples (QCM)
pour le cours "{nom_cours}", à partir du contenu suivant :

---
{texte}
---{bloc_examens}

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


def prompt_quiz_ecrit(nom_cours: str, texte: str, nb_questions: int, examens_passes: str = "") -> str:
    """Questions à réponse libre (pas de choix multiples) : chaque question a une
    'reponse_modele' qui servira ensuite à corriger la réponse de l'étudiant."""
    bloc_examens = _bloc_examens_passes(
        examens_passes,
        "inspire-toi de leur style de questions (souvent plus développées qu'un simple "
        "QCM) et de leurs notions abordées pour composer ces questions.",
    )

    return f"""Tu es un professeur universitaire qui prépare des questions à réponse
écrite (pas de choix multiples : l'étudiant doit rédiger sa réponse) pour le cours
"{nom_cours}", à partir du contenu suivant :

---
{texte}
---{bloc_examens}

Génère exactement {nb_questions} questions ouvertes couvrant l'ensemble du contenu
(varie les notions abordées), qui demandent une réponse rédigée courte (quelques
phrases), pas juste un mot.

Pour chaque question, fournis :
- "enonce" : l'énoncé de la question
- "reponse_modele" : une réponse modèle complète et correcte, qui servira de référence
  pour corriger la réponse de l'étudiant (les points clés attendus, pas forcément mot
  pour mot)

Réponds uniquement avec un objet JSON valide contenant une clé "questions" qui est
une liste de {nb_questions} objets avec ces 2 clés. Pas de texte avant ou après, en français."""


def prompt_correction_ecrite(paires: list[dict]) -> str:
    """`paires` : liste de {"enonce", "reponse_modele", "reponse_etudiant"}.

    Une seule requête pour corriger toutes les réponses d'un coup (plutôt qu'un
    appel par question), pour économiser le quota IA."""
    blocs = []
    for i, p in enumerate(paires):
        blocs.append(
            f"""Question {i + 1} : {p['enonce']}
Réponse modèle : {p['reponse_modele']}
Réponse de l'étudiant : {p['reponse_etudiant'] or "(pas de réponse donnée)"}"""
        )
    bloc_questions = "\n\n".join(blocs)

    return f"""Tu es un professeur universitaire qui corrige les réponses écrites d'un
étudiant, en comparant chacune à sa réponse modèle. Sois indulgent sur la formulation
(ce n'est pas mot pour mot qui compte) mais strict sur le contenu : la réponse doit
couvrir les points clés de la réponse modèle pour être jugée correcte.

{bloc_questions}

Pour chaque question, dans l'ordre, donne :
- "correcte" : true si la réponse de l'étudiant couvre les points clés attendus, false sinon
- "commentaire" : un court retour expliquant ce qui est bon ou ce qui manque (2-3 phrases)

Réponds uniquement avec un objet JSON valide contenant une clé "resultats" qui est
une liste de {len(paires)} objets avec ces 2 clés, dans le même ordre que les questions
ci-dessus. Pas de texte avant ou après, en français."""
