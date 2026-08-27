"""Toutes les opérations de lecture/écriture sur la base de données.

Aucune page Streamlit ne doit écrire du SQL directement : tout passe par ici.
Ça garde le code simple et permettra plus tard d'ajouter des utilisateurs/partage
sans toucher aux pages.
"""

import json
import secrets as _secrets
import string

from core.db import get_connection

_ALPHABET_CODE = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1I")


def generer_code_licence() -> str:
    """Génère un code de licence lisible, du style AB3F-K9QZ-7TMN."""
    brut = "".join(_secrets.choice(_ALPHABET_CODE) for _ in range(12))
    return "-".join(brut[i : i + 4] for i in range(0, 12, 4))

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

def ajouter_document(cours_id: int, nom_original: str, type_fichier: str, chemin_stocke: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO documents (cours_id, nom_original, type_fichier, chemin_stocke)
               VALUES (?, ?, ?, ?)""",
            (cours_id, nom_original, type_fichier, chemin_stocke),
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


def obtenir_document(document_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        return dict(row) if row else None


def supprimer_document(document_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))


def texte_complet_du_cours(cours_id: int) -> str:
    """Concatène le texte extrait de tous les documents d'un cours."""
    docs = lister_documents(cours_id)
    morceaux = [
        f"--- Document : {d['nom_original']} ---\n{d['texte_extrait']}"
        for d in docs
        if d.get("texte_extrait")
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
                      bonne_reponse_index: int, explication: str = ""):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO questions (quiz_id, ordre, enonce, choix_json, bonne_reponse_index, explication)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (quiz_id, ordre, enonce, json.dumps(choix, ensure_ascii=False), bonne_reponse_index, explication),
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
                      duree_secondes: int | None, reponses: list[int]) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO tentatives (quiz_id, phase, score, score_max, duree_secondes, reponses_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (quiz_id, phase, score, score_max, duree_secondes, json.dumps(reponses)),
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


# --- Licences ----------------------------------------------------------------
# Un code de licence est créé par le vendeur (page Administration) après un paiement,
# puis donné au client. Sans un code valide, personne ne peut entrer dans l'appli
# en mode partagé : c'est la vraie barrière de paiement.

def creer_licence(code: str, note: str = "") -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO licences (code, statut, note) VALUES (?, 'disponible', ?)",
            (code, note),
        )


def obtenir_licence(code: str) -> dict | None:
    """Recherche insensible à la casse : peu importe comment le client tape son code."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM licences WHERE UPPER(code) = UPPER(?)", (code,)
        ).fetchone()
        return dict(row) if row else None


def activer_licence(code: str, prenom_client: str) -> None:
    """Marque une licence 'disponible' comme attribuée à ce prénom, la première fois
    qu'elle est utilisée avec succès. Ne fait rien si elle est déjà attribuée."""
    with get_connection() as conn:
        conn.execute(
            """UPDATE licences SET statut = 'attribuee', prenom_client = ?,
               activee_le = datetime('now')
               WHERE UPPER(code) = UPPER(?) AND statut = 'disponible'""",
            (prenom_client, code),
        )


def lister_licences() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM licences ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def revoquer_licence(code: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE licences SET statut = 'revoquee' WHERE UPPER(code) = UPPER(?)", (code,)
        )


def reactiver_licence(code: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE licences SET statut = 'attribuee' WHERE UPPER(code) = UPPER(?) AND statut = 'revoquee'",
            (code,),
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
