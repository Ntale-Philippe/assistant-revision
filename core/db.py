"""Connexion SQLite et création du schéma de la base de données."""

import sqlite3
from contextlib import contextmanager

from core.config import DB_PATH, ensure_dirs

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS cours (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    description TEXT,
    proprietaire TEXT NOT NULL DEFAULT 'moi',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cours_id INTEGER NOT NULL REFERENCES cours(id) ON DELETE CASCADE,
    nom_original TEXT NOT NULL,
    type_fichier TEXT NOT NULL,
    chemin_stocke TEXT NOT NULL,
    texte_extrait TEXT,
    statut_extraction TEXT DEFAULT 'en_attente',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS syntheses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cours_id INTEGER NOT NULL REFERENCES cours(id) ON DELETE CASCADE,
    synthese_md TEXT,
    contexte_md TEXT,
    notions_examen_md TEXT,
    a_retenir_md TEXT,
    fun_facts_md TEXT,
    version INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS quiz (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cours_id INTEGER NOT NULL REFERENCES cours(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    duree_minutes INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER NOT NULL REFERENCES quiz(id) ON DELETE CASCADE,
    ordre INTEGER,
    enonce TEXT NOT NULL,
    choix_json TEXT NOT NULL,
    bonne_reponse_index INTEGER NOT NULL,
    explication TEXT
);

CREATE TABLE IF NOT EXISTS tentatives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER NOT NULL REFERENCES quiz(id) ON DELETE CASCADE,
    phase TEXT NOT NULL,
    score INTEGER NOT NULL,
    score_max INTEGER NOT NULL,
    duree_secondes INTEGER,
    reponses_json TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


@contextmanager
def get_connection():
    """Ouvre une connexion SQLite courte (évite les soucis de threads avec Streamlit)."""
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Crée les tables si elles n'existent pas encore. À appeler au démarrage de l'app."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        _migrer_si_besoin(conn)


def _migrer_si_besoin(conn: sqlite3.Connection):
    """Ajoute les colonnes apparues après la première version du schéma,
    pour ne pas casser une base de données déjà créée avant leur ajout."""
    colonnes = {row["name"] for row in conn.execute("PRAGMA table_info(cours)")}
    if "proprietaire" not in colonnes:
        conn.execute("ALTER TABLE cours ADD COLUMN proprietaire TEXT NOT NULL DEFAULT 'moi'")
