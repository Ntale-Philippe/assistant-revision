import sys, json
sys.path.insert(0, ".")
from core.db import get_connection

cours_id = 39

with get_connection() as conn:
    # document
    conn.execute(
        "INSERT INTO documents (cours_id, nom_original, type_fichier, chemin_stocke, texte_extrait, statut_extraction, categorie) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (cours_id, "note.txt", "txt", "test", "Le foie filtre le sang et produit la bile.", "ok", "cours"),
    )
    # synthese
    conn.execute(
        "INSERT INTO syntheses (cours_id, synthese_md, contexte_md, notions_examen_md, a_retenir_md, fun_facts_md, version) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (cours_id, "Résumé test", "Contexte test", "Notions test", "A retenir test", "Fun facts test", 1),
    )
    # quiz diagnostique + tentative avant/apres
    cur = conn.execute("INSERT INTO quiz (cours_id, type, duree_minutes) VALUES (?, ?, ?)", (cours_id, "diagnostique", None))
    quiz_diag_id = cur.lastrowid
    conn.execute(
        "INSERT INTO questions (quiz_id, ordre, enonce, choix_json, bonne_reponse_index, explication, type_question) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (quiz_diag_id, 1, "Q1?", json.dumps(["a", "b", "c", "d"]), 0, "expl", "choix_multiple"),
    )
    conn.execute(
        "INSERT INTO tentatives (quiz_id, phase, score, score_max, duree_secondes, reponses_json) VALUES (?, ?, ?, ?, ?, ?)",
        (quiz_diag_id, "avant", 1, 1, 60, json.dumps([0])),
    )
    conn.execute(
        "INSERT INTO tentatives (quiz_id, phase, score, score_max, duree_secondes, reponses_json) VALUES (?, ?, ?, ?, ?, ?)",
        (quiz_diag_id, "apres", 1, 1, 55, json.dumps([0])),
    )
    # quiz examen_blanc (existant, comme le ferait un vieux compte)
    cur = conn.execute("INSERT INTO quiz (cours_id, type, duree_minutes) VALUES (?, ?, ?)", (cours_id, "examen_blanc", 20))
    quiz_examen_id = cur.lastrowid
    conn.execute(
        "INSERT INTO questions (quiz_id, ordre, enonce, choix_json, bonne_reponse_index, explication, type_question) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (quiz_examen_id, 1, "QE1?", json.dumps(["a", "b", "c", "d"]), 0, "expl", "choix_multiple"),
    )
    conn.execute(
        "INSERT INTO tentatives (quiz_id, phase, score, score_max, duree_secondes, reponses_json) VALUES (?, ?, ?, ?, ?, ?)",
        (quiz_examen_id, "examen_blanc", 1, 1, 300, json.dumps([0])),
    )
    # quiz reponse_ecrite (existant)
    cur = conn.execute("INSERT INTO quiz (cours_id, type, duree_minutes) VALUES (?, ?, ?)", (cours_id, "reponse_ecrite", 15))
    quiz_ecrit_id = cur.lastrowid
    conn.execute(
        "INSERT INTO questions (quiz_id, ordre, enonce, choix_json, bonne_reponse_index, explication, type_question, reponse_modele) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (quiz_ecrit_id, 1, "QW1?", json.dumps([]), -1, "expl", "ecrite", "reponse modele"),
    )
    conn.execute(
        "INSERT INTO tentatives (quiz_id, phase, score, score_max, duree_secondes, reponses_json, details_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (quiz_ecrit_id, "reponse_ecrite", 1, 1, 400, json.dumps(["reponse"]), json.dumps([{"correcte": True, "commentaire": "ok"}])),
    )
    # messages chat (3 questions - au dela de la limite gratuite)
    for i in range(3):
        conn.execute(
            "INSERT INTO messages_chat (cours_id, role, contenu) VALUES (?, ?, ?)",
            (cours_id, "utilisateur", f"question {i+1}"),
        )
        conn.execute(
            "INSERT INTO messages_chat (cours_id, role, contenu) VALUES (?, ?, ?)",
            (cours_id, "assistant", f"reponse {i+1}"),
        )

print("SEED_OK, cours_id =", cours_id)
