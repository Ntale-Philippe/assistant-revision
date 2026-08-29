"""Toutes les opérations de lecture/écriture sur la base de données.

Aucune page Streamlit ne doit écrire du SQL directement : tout passe par ici.
Ça garde le code simple et permettra plus tard d'ajouter des utilisateurs/partage
sans toucher aux pages.
"""

import json

from core.db import get_connection

# --- Cours -----------------------------------------------------------------
# Chaque cours appartient à un "proprietaire" (le prénom/pseudo de la personne).
# Ça sépare complètement les espaces quand plusieurs personnes partagent la même appli.

def creer_cours(proprietaire: str, nom: str, description: str = "") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO cours (nom, description, proprietaire) VALUES (?, ?, ?)",
            (nom, description, proprietaire),
        )
        return cur.lastrowid


def lister_cours(proprietaire: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM cours WHERE proprietaire = ? ORDER BY created_at DESC",
            (proprietaire,),
        ).fetchall()
        return [dict(r) for r in rows]


def obtenir_cours(cours_id: int, proprietaire: str) -> dict | None:
    """Ne renvoie le cours que s'il appartient bien à ce proprietaire (sinon None)."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM cours WHERE id = ? AND proprietaire = ?", (cours_id, proprietaire)
        ).fetchone()
        return dict(row) if row else None


def supprimer_cours(cours_id: int, proprietaire: str):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM cours WHERE id = ? AND proprietaire = ?", (cours_id, proprietaire)
        )


# --- Documents ---------------------------------------------------------------

def ajouter_document(cours_id: int, nom_original: str, type_fichier: str, chemin_stocke: str,
                      categorie: str = "cours") -> int:
    """`categorie` : 'cours' (notes normales, par défaut) ou 'examen_passe' (ancien
    examen déposé comme référence — jamais mélangé au contenu du cours)."""
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO documents (cours_id, nom_original, type_fichier, chemin_stocke, categorie)
               VALUES (?, ?, ?, ?, ?)""",
            (cours_id, nom_original, type_fichier, chemin_stocke, categorie),
        )
        return cur.lastrowid


def lister_documents(cours_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM documents WHERE cours_id = ? ORDER BY created_at", (cours_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def maj_texte_extrait(document_id: int, texte: str, statut: str = "ok"):
    with get_connection() as conn:
        conn.execute(
            "UPDATE documents SET texte_extrait = ?, statut_extraction = ? WHERE id = ?",
            (texte, statut, document_id),
        )


def supprimer_document(document_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))


def texte_complet_du_cours(cours_id: int) -> str:
    """Concatène le texte extrait des documents de *cours* (pas les anciens examens,
    voir texte_examens_passes)."""
    docs = lister_documents(cours_id)
    morceaux = [
        f"--- Document : {d['nom_original']} ---\n{d['texte_extrait']}"
        for d in docs
        if d.get("texte_extrait") and d.get("categorie", "cours") == "cours"
    ]
    return "\n\n".join(morceaux)


def texte_examens_passes(cours_id: int) -> str:
    """Concatène le texte extrait des anciens examens déposés pour ce cours (vide
    si l'étudiant n'en a pas déposé)."""
    docs = lister_documents(cours_id)
    morceaux = [
        f"--- Ancien examen : {d['nom_original']} ---\n{d['texte_extrait']}"
        for d in docs
        if d.get("texte_extrait") and d.get("categorie") == "examen_passe"
    ]
    return "\n\n".join(morceaux)


# --- Synthèses -----------------------------------------------------------------

def sauver_synthese(cours_id: int, synthese: dict) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO syntheses
               (cours_id, synthese_md, contexte_md, notions_examen_md, a_retenir_md, fun_facts_md)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                cours_id,
                synthese.get("synthese", ""),
                synthese.get("contexte", ""),
                synthese.get("notions_examen", ""),
                synthese.get("a_retenir", ""),
                synthese.get("fun_facts", ""),
            ),
        )
        return cur.lastrowid


def derniere_synthese(cours_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM syntheses WHERE cours_id = ? ORDER BY created_at DESC LIMIT 1",
            (cours_id,),
        ).fetchone()
        return dict(row) if row else None


# --- Quiz & questions ------------------------------------------------------

def creer_quiz(cours_id: int, type_quiz: str, duree_minutes: int | None = None) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO quiz (cours_id, type, duree_minutes) VALUES (?, ?, ?)",
            (cours_id, type_quiz, duree_minutes),
        )
        return cur.lastrowid


def ajouter_question(quiz_id: int, ordre: int, enonce: str, choix: list[str],
                      bonne_reponse_index: int, explication: str = "",
                      type_question: str = "choix_multiple", reponse_modele: str | None = None):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO questions
               (quiz_id, ordre, enonce, choix_json, bonne_reponse_index, explication,
                type_question, reponse_modele)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (quiz_id, ordre, enonce, json.dumps(choix, ensure_ascii=False), bonne_reponse_index,
             explication, type_question, reponse_modele),
        )


def obtenir_quiz(quiz_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM quiz WHERE id = ?", (quiz_id,)).fetchone()
        return dict(row) if row else None


def obtenir_quiz_par_type(cours_id: int, type_quiz: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM quiz WHERE cours_id = ? AND type = ? ORDER BY created_at DESC LIMIT 1",
            (cours_id, type_quiz),
        ).fetchone()
        return dict(row) if row else None


def lister_questions(quiz_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM questions WHERE quiz_id = ? ORDER BY ordre", (quiz_id,)
        ).fetchall()
        questions = []
        for r in rows:
            q = dict(r)
            q["choix"] = json.loads(q["choix_json"])
            questions.append(q)
        return questions


# --- Tentatives (résultats de quiz) ----------------------------------------

def sauver_tentative(quiz_id: int, phase: str, score: int, score_max: int,
                      duree_secondes: int | None, reponses: list, details: list[dict] | None = None) -> int:
    """`details` (optionnel) : feedback par question pour les questions à réponse
    écrite, ex. [{"correcte": True, "commentaire": "..."}]."""
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO tentatives
               (quiz_id, phase, score, score_max, duree_secondes, reponses_json, details_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (quiz_id, phase, score, score_max, duree_secondes, json.dumps(reponses, ensure_ascii=False),
             json.dumps(details, ensure_ascii=False) if details is not None else None),
        )
        return cur.lastrowid


def lister_tentatives(quiz_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM tentatives WHERE quiz_id = ? ORDER BY created_at", (quiz_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def derniere_tentative(quiz_id: int, phase: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tentatives WHERE quiz_id = ? AND phase = ? ORDER BY created_at DESC LIMIT 1",
            (quiz_id, phase),
        ).fetchone()
        return dict(row) if row else None


def historique_tentatives(cours_id: int, type_quiz: str) -> list[dict]:
    """Toutes les tentatives passées pour ce type de quiz sur ce cours, TOUTES
    générations confondues : régénérer un quiz (examen blanc, questions écrites)
    crée un nouveau quiz_id, mais les anciennes tentatives restent consultables ici
    au lieu de devenir invisibles. Chaque tentative renvoyée inclut ses propres
    questions (celles du quiz tel qu'il était au moment de la tentative) et ses
    réponses/détails déjà décodés (plus besoin de json.loads côté appelant)."""
    with get_connection() as conn:
        quiz_ids = [
            r["id"]
            for r in conn.execute(
                "SELECT id FROM quiz WHERE cours_id = ? AND type = ? ORDER BY created_at",
                (cours_id, type_quiz),
            ).fetchall()
        ]

    resultat = []
    for quiz_id in quiz_ids:
        questions = lister_questions(quiz_id)
        for tentative in lister_tentatives(quiz_id):
            tentative["questions"] = questions
            tentative["reponses"] = (
                json.loads(tentative["reponses_json"]) if tentative.get("reponses_json") else []
            )
            tentative["details"] = (
                json.loads(tentative["details_json"]) if tentative.get("details_json") else None
            )
            resultat.append(tentative)

    resultat.sort(key=lambda t: t["created_at"], reverse=True)
    return resultat


# --- Profil (facultatif, pour personnaliser "à retenir pour la vie") ---------

def obtenir_profil(identifiant: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM profils WHERE identifiant = ?", (identifiant,)
        ).fetchone()
        return dict(row) if row else None


def sauver_profil(identifiant: str, faculte: str, reve: str):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO profils (identifiant, faculte, reve, updated_at)
               VALUES (?, ?, ?, datetime('now'))
               ON CONFLICT(identifiant) DO UPDATE SET
                   faculte = excluded.faculte,
                   reve = excluded.reve,
                   updated_at = excluded.updated_at""",
            (identifiant, faculte, reve),
        )


# --- Chat (discussion libre sur un cours) ------------------------------------

def ajouter_message_chat(cours_id: int, role: str, contenu: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO messages_chat (cours_id, role, contenu) VALUES (?, ?, ?)",
            (cours_id, role, contenu),
        )
        return cur.lastrowid


def lister_messages_chat(cours_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM messages_chat WHERE cours_id = ? ORDER BY created_at", (cours_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def vider_chat(cours_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM messages_chat WHERE cours_id = ?", (cours_id,))
