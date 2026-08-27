"""Génère un fichier Excel récapitulatif de tous les codes de licence vendus."""

import io

import pandas as pd

from core import repository

NOMS_COLONNES = {
    "code": "Code",
    "prenom_client": "Client",
    "statut_affiche": "Statut",
    "montant": "Montant payé",
    "devise": "Devise",
    "duree_jours": "Durée (jours)",
    "created_at": "Créé le",
    "activee_le": "Activé le",
    "expire_le": "Expire le",
    "jours_restants": "Jours restants",
    "a_relancer_affiche": "À relancer ?",
    "note": "Note",
}

BADGES_STATUT = {"disponible": "Non utilisé", "attribuee": "Actif", "revoquee": "Révoqué"}


def generer_excel_licences() -> bytes:
    """Construit un fichier .xlsx (en mémoire) avec toutes les infos utiles sur les
    codes vendus : qui, combien, quand, et qui doit être relancé pour repayer."""
    licences = repository.lister_licences()

    lignes = []
    for licence in licences:
        expiree = bool(licence.get("expiree"))
        statut_affiche = "Expiré" if expiree and licence["statut"] != "revoquee" else BADGES_STATUT.get(
            licence["statut"], licence["statut"]
        )
        ligne = dict(licence)
        ligne["statut_affiche"] = statut_affiche
        ligne["a_relancer_affiche"] = "Oui" if licence.get("a_relancer") else "Non"
        lignes.append(ligne)

    df = pd.DataFrame(lignes)
    if df.empty:
        df = pd.DataFrame(columns=list(NOMS_COLONNES.keys()))
    df = df[[c for c in NOMS_COLONNES if c in df.columns]]
    df = df.rename(columns=NOMS_COLONNES)

    tampon = io.BytesIO()
    with pd.ExcelWriter(tampon, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Codes de licence")
        feuille = writer.sheets["Codes de licence"]
        for colonne in feuille.columns:
            largeur = max((len(str(cellule.value)) for cellule in colonne if cellule.value is not None), default=10)
            feuille.column_dimensions[colonne[0].column_letter].width = min(largeur + 2, 40)

    return tampon.getvalue()
