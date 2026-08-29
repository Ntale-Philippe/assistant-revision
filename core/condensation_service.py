"""Condensation du texte d'un cours quand il est trop volumineux.

Quand un cours a beaucoup de documents (ou des documents très longs), envoyer tout
leur texte d'un coup à l'IA rend la génération lente et augmente le risque de se
heurter aux limites gratuites de Google. Ici, on découpe le texte en morceaux plus
petits, on demande à l'IA de résumer chaque morceau (en gardant tout ce qui compte),
puis on recolle ces résumés : le texte final envoyé pour la synthèse/le quiz est
beaucoup plus court, sans perdre les notions importantes.
"""

from core.config import SEUIL_CONDENSATION_CARACTERES, TAILLE_MORCEAU_CONDENSATION
from core.gemini_client import generer_texte
from core.prompts import prompt_condensation


def _decouper_texte(texte: str, taille: int) -> list[str]:
    """Découpe `texte` en morceaux d'environ `taille` caractères, en coupant sur un
    saut de paragraphe quand c'est possible pour ne pas trancher au milieu d'une idée."""
    if len(texte) <= taille:
        return [texte]

    morceaux = []
    reste = texte
    while len(reste) > taille:
        limite = reste.rfind("\n\n", 0, taille)
        if limite < taille // 2:
            limite = taille  # pas de bonne coupure trouvée : on coupe net
        morceaux.append(reste[:limite])
        reste = reste[limite:]
    if reste.strip():
        morceaux.append(reste)
    return morceaux


def texte_pret_pour_ia(texte: str, api_key: str) -> str:
    """Retourne le texte tel quel s'il est de taille raisonnable, ou une version
    condensée (résumée morceau par morceau, puis recollée) s'il est très volumineux."""
    if len(texte) <= SEUIL_CONDENSATION_CARACTERES:
        return texte

    morceaux = _decouper_texte(texte, TAILLE_MORCEAU_CONDENSATION)
    resumes = [generer_texte(prompt_condensation(morceau), api_key) for morceau in morceaux]
    return "\n\n".join(resumes)
