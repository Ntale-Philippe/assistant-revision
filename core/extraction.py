"""Extraction du texte d'un document (txt, pdf, image) pour alimenter l'IA."""

from pathlib import Path

from pypdf import PdfReader

from core.gemini_client import lire_image, lire_pdf
from core.prompts import PROMPT_OCR_IMAGE, PROMPT_OCR_PDF_SCANNE

# En dessous de ce nombre de caractères, on considère qu'un PDF est un scan
# (pas de couche texte) et on le fait lire directement par Gemini.
SEUIL_TEXTE_PDF_INSUFFISANT = 50

MIME_PAR_EXTENSION = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}


def type_fichier_depuis_nom(nom_fichier: str) -> str:
    ext = Path(nom_fichier).suffix.lower().lstrip(".")
    if ext == "pdf":
        return "pdf"
    if ext in MIME_PAR_EXTENSION:
        return "image"
    return "texte"


def extraire_texte(chemin_stocke: str, nom_original: str, api_key: str) -> str:
    """Retourne le texte extrait d'un document, quel que soit son format."""
    type_fichier = type_fichier_depuis_nom(nom_original)
    chemin = Path(chemin_stocke)

    if type_fichier == "texte":
        return chemin.read_text(encoding="utf-8", errors="replace")

    if type_fichier == "image":
        ext = Path(nom_original).suffix.lower().lstrip(".")
        mime_type = MIME_PAR_EXTENSION.get(ext, "image/png")
        image_bytes = chemin.read_bytes()
        return lire_image(image_bytes, mime_type, PROMPT_OCR_IMAGE, api_key)

    if type_fichier == "pdf":
        pdf_bytes = chemin.read_bytes()
        texte = _extraire_texte_pdf_local(chemin)
        if len(texte.strip()) < SEUIL_TEXTE_PDF_INSUFFISANT:
            # PDF probablement scanné (pas de couche texte) : on demande à Gemini de le lire.
            return lire_pdf(pdf_bytes, PROMPT_OCR_PDF_SCANNE, api_key)
        return texte

    raise ValueError(f"Type de fichier non supporté : {nom_original}")


def _extraire_texte_pdf_local(chemin: Path) -> str:
    try:
        reader = PdfReader(str(chemin))
        pages_texte = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages_texte)
    except Exception:
        return ""
