"""Toutes les opérations de lecture/écriture sur la base de données.

Aucune page Streamlit ne doit écrire du SQL directement : tout passe par ici.
Ça garde le code simple et permettra plus tard d'ajouter des utilisateurs/partage
sans toucher aux pages.
"""

import json

from core.config import IDENTIFIANT_DEMO
from core.db import get_connection

# Identifiants à exclure des statistiques "vrais étudiants" : le compte solo local
# du propriétaire et le cours de démonstration publique, qui ne représentent pas
# de vrais inscrits.
_IDENTIFIANTS_EXCLUS = ("moi", IDENTIFIANT_DEMO)

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
    examen déposé comme référence — jamais mélangé au contenu du cours).

    Crée toujours un nouveau document — voir obtenir_document_par_nom() pour
    détecter un doublon *avant* d'appeler cette fonction et demander à
    l'utilisateur s'il veut remplacer ou annuler, plutôt que d'en créer un
    deuxième silencieusement."""
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO documents (cours_id, nom_original, type_fichier, chemin_stocke, categorie)
               VALUES (?, ?, ?, ?, ?)""",
            (cours_id, nom_original, type_fichier, chemin_stocke, categorie),
        )
        return cur.lastrowid


def obtenir_document_par_nom(cours_id: int, nom_original: str, categorie: str) -> dict | None:
    """Cherche un document existant du même nom (et catégorie) pour ce cours —
    utilisé pour détecter un doublon avant d'ajouter un nouveau fichier."""
    with get_connection() as conn:
        row = conn.execute(
            """SELECT * FROM documents WHERE cours_id = ? AND nom_original = ? AND categorie = ?
               ORDER BY created_at DESC LIMIT 1""",
            (cours_id, nom_original, categorie),
        ).fetchone()
        return dict(row) if row else None


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


def lister_sans_fautes(identifiant: str) -> list[dict]:
    """Tous les sans-fautes (score = score_max) obtenus par cet étudiant sur les
    deux examens chronométrés (examen blanc, examen écrit), TOUS cours confondus -
    purement un badge personnel à consulter sur la page Progression, qui ne
    débloque rien et ne s'échange contre rien (décision produit du 2026-08-30 :
    éviter tout système de "monnaie" à faire farmer)."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT t.score, t.score_max, t.created_at, q.type AS type_quiz, c.nom AS cours_nom
               FROM tentatives t
               JOIN quiz q ON q.id = t.quiz_id
               JOIN cours c ON c.id = q.cours_id
               WHERE c.proprietaire = ?
                 AND q.type IN ('examen_blanc', 'reponse_ecrite')
                 AND t.score_max > 0
                 AND t.score = t.score_max
               ORDER BY t.created_at DESC""",
            (identifiant,),
        ).fetchall()
        return [dict(r) for r in rows]


# --- Profil (facultatif, pour personnaliser "à retenir pour la vie") ---------

def obtenir_profil(identifiant: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM profils WHERE identifiant = ?", (identifiant,)
        ).fetchone()
        return dict(row) if row else None


def sauver_profil(identifiant: str, faculte: str, reve: str, pays: str = "", surnom: str = ""):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO profils (identifiant, faculte, reve, pays, surnom, updated_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(identifiant) DO UPDATE SET
                   faculte = excluded.faculte,
                   reve = excluded.reve,
                   pays = excluded.pays,
                   surnom = excluded.surnom,
                   updated_at = excluded.updated_at""",
            (identifiant, faculte, reve, pays, surnom),
        )


def enregistrer_prenom(identifiant: str, prenom: str):
    """Retient le prénom affiché à chaque connexion (indépendamment du profil
    facultatif) : sert uniquement à ce que le propriétaire de l'appli reconnaisse
    qui est qui dans l'outil d'activation premium (l'identifiant est un hash
    illisible) - ne touche jamais aux autres champs du profil s'il existe déjà."""
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO profils (identifiant, prenom) VALUES (?, ?)
               ON CONFLICT(identifiant) DO UPDATE SET prenom = excluded.prenom""",
            (identifiant, prenom),
        )


def prenom_deja_utilise_ailleurs(prenom: str, identifiant_actuel: str) -> bool:
    """Vrai si ce prénom est déjà associé à un AUTRE identifiant (donc un autre mot
    de passe, puisque l'identifiant = hash(prénom + mot de passe)). Sert à repérer
    une probable erreur de frappe sur le mot de passe plutôt qu'un vrai nouveau
    visiteur - cas réel rencontré : la même personne s'était retrouvée avec 3
    espaces vides différents, sans aucun moyen de le remarquer avant de commencer
    à déposer des documents dans le mauvais."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM profils WHERE LOWER(prenom) = LOWER(?) AND identifiant != ? LIMIT 1",
            (prenom.strip(), identifiant_actuel),
        ).fetchone()
        return row is not None


def a_deja_un_espace(identifiant: str) -> bool:
    """Vrai si cet identifiant précis a déjà été utilisé (au moins un cours créé,
    ou un profil déjà enregistré) - permet de ne montrer l'avertissement de prénom
    en doublon que pour un espace tout neuf, jamais pour quelqu'un qui revient
    simplement sur son propre espace déjà connu."""
    with get_connection() as conn:
        if conn.execute("SELECT 1 FROM cours WHERE proprietaire = ? LIMIT 1", (identifiant,)).fetchone():
            return True
        return conn.execute("SELECT 1 FROM profils WHERE identifiant = ? LIMIT 1", (identifiant,)).fetchone() is not None


# --- Accès premium -------------------------------------------------------------
# Pas de code à acheter/taper : l'étudiant paie hors appli (mobile money) et
# prévient le propriétaire, qui active manuellement l'accès depuis la page cachée
# Statistiques avancées. Voir aussi core/premium.py pour la vérification d'accès.

def est_premium(identifiant: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT expire_le FROM premium WHERE identifiant = ?", (identifiant,)
        ).fetchone()
        if not row:
            return False
        if row["expire_le"] is None:
            return True
        return row["expire_le"] > _maintenant_iso()


def a_acces_debloque(identifiant: str) -> bool:
    """À utiliser partout dans l'interface à la place de est_premium() directement :
    tant que PREMIUM_ACTIF (core/config.py) est à False, tout le monde reste débloqué
    (le paywall est construit mais pas encore lancé). Une fois PREMIUM_ACTIF passé à
    True, redevient équivalent à est_premium()."""
    from core.config import PREMIUM_ACTIF
    return (not PREMIUM_ACTIF) or est_premium(identifiant)


def _maintenant_iso() -> str:
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())


def activer_premium(identifiant: str, jours: int | None, montant: float | None, devise: str, note: str = ""):
    """`jours` : durée de l'accès (None = permanent, jamais d'expiration)."""
    expire_le = None
    if jours is not None:
        import datetime
        expire_le = (datetime.datetime.utcnow() + datetime.timedelta(days=jours)).strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO premium (identifiant, active_le, expire_le, montant, devise, note)
               VALUES (?, datetime('now'), ?, ?, ?, ?)
               ON CONFLICT(identifiant) DO UPDATE SET
                   active_le = datetime('now'),
                   expire_le = excluded.expire_le,
                   montant = excluded.montant,
                   devise = excluded.devise,
                   note = excluded.note""",
            (identifiant, expire_le, montant, devise, note),
        )


def desactiver_premium(identifiant: str):
    with get_connection() as conn:
        conn.execute("DELETE FROM premium WHERE identifiant = ?", (identifiant,))


def lister_candidats_premium() -> list[dict]:
    """Tous les vrais étudiants (hors compte solo/démo), avec leur prénom connu,
    leurs cours, et leur statut premium actuel - pour que le propriétaire retrouve
    facilement qui activer après un paiement reçu par mobile money."""
    with get_connection() as conn:
        identifiants_cours = conn.execute(
            f"""SELECT proprietaire, GROUP_CONCAT(nom, ', ') as cours_noms, COUNT(*) as nb_cours
                FROM cours WHERE proprietaire NOT IN ({",".join("?" for _ in _IDENTIFIANTS_EXCLUS)})
                GROUP BY proprietaire""",
            _IDENTIFIANTS_EXCLUS,
        ).fetchall()
        profils_rows = conn.execute("SELECT identifiant, prenom, surnom FROM profils").fetchall()
        premium_rows = conn.execute("SELECT identifiant, expire_le, montant, devise FROM premium").fetchall()

    profils = {r["identifiant"]: r for r in profils_rows}
    premiums = {r["identifiant"]: dict(r) for r in premium_rows}

    resultat = []
    for r in identifiants_cours:
        identifiant = r["proprietaire"]
        premium_info = premiums.get(identifiant)
        profil = profils.get(identifiant)
        resultat.append({
            "identifiant": identifiant,
            "prenom": (profil["prenom"] if profil else None) or "(prénom inconnu)",
            # Distingue deux personnes ayant le même prénom (ex: deux "Philippe") -
            # sans ça, impossible de savoir laquelle demande un renouvellement.
            "surnom": (profil["surnom"] if profil else None) or "",
            "cours_noms": r["cours_noms"],
            "nb_cours": r["nb_cours"],
            "est_premium": est_premium(identifiant),
            "premium_expire_le": premium_info["expire_le"] if premium_info else None,
        })
    resultat.sort(key=lambda x: x["prenom"].lower())
    return resultat


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


def compter_questions_chat(cours_id: int) -> int:
    """Nombre de questions déjà posées (pas les réponses) sur ce cours - sert à la
    limite de questions gratuites du chat."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT COUNT(*) as n FROM messages_chat WHERE cours_id = ? AND role = 'utilisateur'",
            (cours_id,),
        ).fetchone()["n"]


def vider_chat(cours_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM messages_chat WHERE cours_id = ?", (cours_id,))


# --- Statistiques ------------------------------------------------------------
# Purement des lectures agrégées sur les tables existantes : aucune nouvelle table,
# aucun impact sur les données. Le compte solo local ('moi') et le cours de
# démonstration ('demo-public') sont toujours exclus des chiffres "vrais étudiants".

def statistiques_utilisateur(identifiant: str) -> dict:
    """Chiffres d'un étudiant sur SES propres cours."""
    with get_connection() as conn:
        nb_cours = conn.execute(
            "SELECT COUNT(*) as n FROM cours WHERE proprietaire = ?", (identifiant,)
        ).fetchone()["n"]
        nb_documents = conn.execute(
            """SELECT COUNT(*) as n FROM documents
               WHERE cours_id IN (SELECT id FROM cours WHERE proprietaire = ?)""",
            (identifiant,),
        ).fetchone()["n"]
        nb_syntheses = conn.execute(
            """SELECT COUNT(*) as n FROM syntheses
               WHERE cours_id IN (SELECT id FROM cours WHERE proprietaire = ?)""",
            (identifiant,),
        ).fetchone()["n"]
        tentatives = conn.execute(
            """SELECT score, score_max FROM tentatives
               WHERE quiz_id IN (
                   SELECT id FROM quiz WHERE cours_id IN (
                       SELECT id FROM cours WHERE proprietaire = ?
                   )
               )""",
            (identifiant,),
        ).fetchall()

    nb_tentatives = len(tentatives)
    score_moyen = (
        round(100 * sum(t["score"] / t["score_max"] for t in tentatives if t["score_max"]) / nb_tentatives)
        if nb_tentatives
        else None
    )
    return {
        "nb_cours": nb_cours,
        "nb_documents": nb_documents,
        "nb_syntheses": nb_syntheses,
        "nb_tentatives": nb_tentatives,
        "score_moyen_pourcentage": score_moyen,
    }


def statistiques_globales() -> dict:
    """Chiffres agrégés sur toute l'appli (tous les vrais étudiants confondus)."""
    placeholders = ",".join("?" for _ in _IDENTIFIANTS_EXCLUS)
    with get_connection() as conn:
        nb_inscrits = conn.execute(
            f"SELECT COUNT(DISTINCT proprietaire) as n FROM cours WHERE proprietaire NOT IN ({placeholders})",
            _IDENTIFIANTS_EXCLUS,
        ).fetchone()["n"]
        nb_cours = conn.execute(
            f"SELECT COUNT(*) as n FROM cours WHERE proprietaire NOT IN ({placeholders})",
            _IDENTIFIANTS_EXCLUS,
        ).fetchone()["n"]
        nb_documents = conn.execute(
            f"""SELECT COUNT(*) as n FROM documents
                WHERE cours_id IN (SELECT id FROM cours WHERE proprietaire NOT IN ({placeholders}))""",
            _IDENTIFIANTS_EXCLUS,
        ).fetchone()["n"]
        nb_syntheses = conn.execute(
            f"""SELECT COUNT(*) as n FROM syntheses
                WHERE cours_id IN (SELECT id FROM cours WHERE proprietaire NOT IN ({placeholders}))""",
            _IDENTIFIANTS_EXCLUS,
        ).fetchone()["n"]
        tentatives = conn.execute(
            f"""SELECT score, score_max FROM tentatives
                WHERE quiz_id IN (
                    SELECT id FROM quiz WHERE cours_id IN (
                        SELECT id FROM cours WHERE proprietaire NOT IN ({placeholders})
                    )
                )""",
            _IDENTIFIANTS_EXCLUS,
        ).fetchall()
        nb_pays = conn.execute(
            f"""SELECT COUNT(DISTINCT pays) as n FROM profils
                WHERE pays IS NOT NULL AND pays != ''
                  AND identifiant IN (SELECT DISTINCT proprietaire FROM cours WHERE proprietaire NOT IN ({placeholders}))""",
            _IDENTIFIANTS_EXCLUS,
        ).fetchone()["n"]

    nb_tentatives = len(tentatives)
    score_moyen = (
        round(100 * sum(t["score"] / t["score_max"] for t in tentatives if t["score_max"]) / nb_tentatives)
        if nb_tentatives
        else None
    )
    return {
        "nb_inscrits": nb_inscrits,
        "nb_cours": nb_cours,
        "nb_documents": nb_documents,
        "nb_syntheses": nb_syntheses,
        "nb_tentatives": nb_tentatives,
        "score_moyen_pourcentage": score_moyen,
        "nb_pays_representes": nb_pays,
    }


def insights_admin() -> dict:
    """Indicateurs pensés pour repérer des problèmes concrets et exploitables :
    des cours bloqués à une étape (upload réussi mais jamais de synthèse, etc.),
    des documents en échec d'extraction, la croissance dans le temps..."""
    placeholders = ",".join("?" for _ in _IDENTIFIANTS_EXCLUS)
    with get_connection() as conn:
        cours = conn.execute(
            f"""SELECT id, nom, proprietaire, created_at FROM cours
                WHERE proprietaire NOT IN ({placeholders}) ORDER BY created_at""",
            _IDENTIFIANTS_EXCLUS,
        ).fetchall()
        cours = [dict(c) for c in cours]
        cours_ids = [c["id"] for c in cours]

        documents_en_erreur = []
        cours_vides = []
        cours_sans_synthese = []
        cours_sans_quiz = []

        for c in cours:
            docs = conn.execute(
                "SELECT nom_original, statut_extraction FROM documents WHERE cours_id = ?", (c["id"],)
            ).fetchall()
            if not docs:
                c["statut"] = "vide"
                cours_vides.append(c)
                continue
            for d in docs:
                if d["statut_extraction"] == "erreur":
                    documents_en_erreur.append({
                        "cours": c["nom"], "proprietaire": c["proprietaire"], "document": d["nom_original"],
                    })

            a_une_synthese = conn.execute(
                "SELECT 1 FROM syntheses WHERE cours_id = ? LIMIT 1", (c["id"],)
            ).fetchone()
            if not a_une_synthese:
                c["statut"] = "sans_synthese"
                cours_sans_synthese.append(c)
                continue

            a_un_quiz = conn.execute(
                "SELECT 1 FROM quiz WHERE cours_id = ? LIMIT 1", (c["id"],)
            ).fetchone()
            if not a_un_quiz:
                c["statut"] = "sans_quiz"
                cours_sans_quiz.append(c)
            else:
                c["statut"] = "complet"

        # Score moyen par type de quiz (diagnostique/examen_blanc/reponse_ecrite)
        scores_par_type = {}
        if cours_ids:
            placeholders_cours = ",".join("?" for _ in cours_ids)
            rows = conn.execute(
                f"""SELECT quiz.type as type, tentatives.score as score, tentatives.score_max as score_max
                    FROM tentatives
                    JOIN quiz ON quiz.id = tentatives.quiz_id
                    WHERE quiz.cours_id IN ({placeholders_cours})""",
                cours_ids,
            ).fetchall()
            par_type = {}
            for r in rows:
                par_type.setdefault(r["type"], []).append(r)
            for type_quiz, tents in par_type.items():
                valides = [t for t in tents if t["score_max"]]
                if valides:
                    scores_par_type[type_quiz] = round(
                        100 * sum(t["score"] / t["score_max"] for t in valides) / len(valides)
                    )

        # Croissance : nombre de cours créés par jour
        cours_par_jour = {}
        for c in cours:
            jour = c["created_at"][:10]
            cours_par_jour[jour] = cours_par_jour.get(jour, 0) + 1

        # Répartition géographique (auto-déclarée dans le profil facultatif) : un
        # étudiant qui n'a jamais rempli son pays apparaît sous "Non renseigné"
        # plutôt que d'être ignoré, pour que le total corresponde au nombre d'inscrits.
        identifiants_reels = {c["proprietaire"] for c in cours}
        pays_par_identifiant = {}
        if identifiants_reels:
            placeholders_profils = ",".join("?" for _ in identifiants_reels)
            rows = conn.execute(
                f"SELECT identifiant, pays FROM profils WHERE identifiant IN ({placeholders_profils})",
                tuple(identifiants_reels),
            ).fetchall()
            pays_par_identifiant = {r["identifiant"]: r["pays"] for r in rows}

        repartition_pays = {}
        for identifiant in identifiants_reels:
            pays = (pays_par_identifiant.get(identifiant) or "").strip() or "Non renseigné"
            repartition_pays[pays] = repartition_pays.get(pays, 0) + 1

        # Détail par pays : au-delà du simple décompte d'étudiants, le taux de
        # cours menés à terme (synthèse + quiz) par pays — utile pour repérer si
        # un pays en particulier galère plus que les autres (réseau, appareils...).
        detail_par_pays = {}
        for c in cours:
            pays = (pays_par_identifiant.get(c["proprietaire"]) or "").strip() or "Non renseigné"
            d = detail_par_pays.setdefault(pays, {"nb_cours": 0, "nb_complets": 0, "etudiants": set()})
            d["nb_cours"] += 1
            d["nb_complets"] += 1 if c["statut"] == "complet" else 0
            d["etudiants"].add(c["proprietaire"])
        for pays, d in detail_par_pays.items():
            d["nb_etudiants"] = len(d.pop("etudiants"))
            d["taux_completion"] = round(100 * d["nb_complets"] / d["nb_cours"]) if d["nb_cours"] else 0

    return {
        "nb_cours_total": len(cours),
        "cours_vides": cours_vides,
        "cours_sans_synthese": cours_sans_synthese,
        "cours_sans_quiz": cours_sans_quiz,
        "documents_en_erreur": documents_en_erreur,
        "scores_par_type": scores_par_type,
        "cours_par_jour": cours_par_jour,
        "repartition_pays": repartition_pays,
        "detail_par_pays": detail_par_pays,
    }
