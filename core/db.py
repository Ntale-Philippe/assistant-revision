"""Connexion à la base de données et création du schéma.

Deux modes possibles, choisis automatiquement :
- Local (par défaut) : un fichier SQLite classique (data/app.db) sur ton PC.
- Turso (si TURSO_DATABASE_URL et TURSO_AUTH_TOKEN sont configurés dans les secrets) :
  une base de données hébergée gratuitement, qui survit aux redémarrages/redéploiements
  de l'appli en ligne — contrairement au fichier local, qui peut être effacé quand
  l'appli tourne sur un hébergement comme Streamlit Community Cloud.

Une petite couche de compatibilité (_CompatConnection / _CompatCursor) fait que tout
le reste du code (repository.py) fonctionne à l'identique, peu importe lequel des deux
modes est actif : les lignes sont toujours renvoyées sous forme de dict.
"""

import sqlite3
from contextlib import contextmanager

import streamlit as st

from core.config import DB_PATH, ensure_dirs


def _turso_credentials():
    """Retourne (url, token) si Turso est configuré dans les secrets, sinon (None, None)."""
    try:
        import streamlit as st

        url = st.secrets.get("TURSO_DATABASE_URL")
        token = st.secrets.get("TURSO_AUTH_TOKEN")
        if url and token:
            return url, token
    except Exception:
        pass
    return None, None


class _CompatCursor:
    """Enveloppe un curseur (sqlite3 ou libsql) pour toujours renvoyer des dicts,
    peu importe le pilote utilisé en dessous."""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=()):
        self._cursor.execute(sql, params)
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        return self._vers_dict(row)

    def fetchall(self):
        return [self._vers_dict(r) for r in self._cursor.fetchall()]

    def _vers_dict(self, row):
        if row is None:
            return None
        colonnes = [d[0] for d in self._cursor.description]
        return dict(zip(colonnes, row))

    @property
    def lastrowid(self):
        # On ne se fie pas uniquement à l'attribut du pilote (pas garanti identique
        # partout) : on retombe sur la fonction SQL standard si besoin.
        valeur = getattr(self._cursor, "lastrowid", None)
        if valeur:
            return valeur
        self._cursor.execute("SELECT last_insert_rowid()")
        ligne = self._cursor.fetchone()
        return ligne[0] if ligne else None


class _CompatConnection:
    def __init__(self, connexion_brute):
        self._conn = connexion_brute

    def execute(self, sql, params=()):
        curseur = self._conn.cursor()
        curseur.execute(sql, params)
        return _CompatCursor(curseur)

    def executescript(self, sql):
        for instruction in filter(None, (s.strip() for s in sql.split(";"))):
            self._conn.cursor().execute(instruction)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


@contextmanager
def get_connection():
    """Ouvre une connexion courte (locale ou Turso selon la configuration)."""
    ensure_dirs()
    url, token = _turso_credentials()

    if url and token:
        from core.turso_http import TursoHTTPConnection

        # Turso utilise le préfixe libsql:// pour ses SDK natifs ; en HTTP classique
        # (via `requests`), il faut https://.
        url_http = url.replace("libsql://", "https://", 1)
        brute = TursoHTTPConnection(url_http, token)
    else:
        brute = sqlite3.connect(DB_PATH)

    conn = _CompatConnection(brute)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
    except Exception:
        pass  # certains pilotes distants gèrent déjà ça autrement
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


SCHEMA = """
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
    -- 'cours' (notes normales) ou 'examen_passe' (ancien examen déposé par
    -- l'étudiant, utilisé comme référence pour les notions probables et le style
    -- des quiz, mais jamais mélangé au contenu du cours lui-même).
    categorie TEXT NOT NULL DEFAULT 'cours',
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
    explication TEXT,
    -- 'choix_multiple' (les 3 quiz habituels) ou 'ecrite' (réponse libre, corrigée
    -- par l'IA en comparant à reponse_modele). choix_json/bonne_reponse_index
    -- restent renseignés (avec des valeurs vides/-1) pour les questions écrites,
    -- pour ne pas avoir à assouplir les contraintes NOT NULL sur une base déjà en ligne.
    type_question TEXT NOT NULL DEFAULT 'choix_multiple',
    reponse_modele TEXT
);

CREATE TABLE IF NOT EXISTS tentatives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER NOT NULL REFERENCES quiz(id) ON DELETE CASCADE,
    phase TEXT NOT NULL,
    score INTEGER NOT NULL,
    score_max INTEGER NOT NULL,
    duree_secondes INTEGER,
    reponses_json TEXT,
    -- Détail par question pour les questions à réponse écrite (feedback de l'IA) :
    -- une liste de {"correcte": bool, "commentaire": str}, dans l'ordre des questions.
    details_json TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS licences (
    code TEXT PRIMARY KEY,
    statut TEXT NOT NULL DEFAULT 'disponible',
    note TEXT,
    prenom_client TEXT,
    duree_jours INTEGER NOT NULL DEFAULT 30,
    montant REAL,
    devise TEXT DEFAULT 'USD',
    contact TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    activee_le TEXT,
    expire_le TEXT
);

CREATE TABLE IF NOT EXISTS profils (
    -- Un profil facultatif par personne (identifiant, pas par cours) : sert à
    -- personnaliser la section "à retenir pour la vie" de la synthèse en la reliant
    -- à la filière et à l'objectif de vie de l'étudiant, plutôt que des généralités.
    identifiant TEXT PRIMARY KEY,
    faculte TEXT,
    reve TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages_chat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cours_id INTEGER NOT NULL REFERENCES cours(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    contenu TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


@st.cache_resource
def init_db():
    """Crée les tables si elles n'existent pas encore. À appeler au démarrage de l'app.

    Mis en cache (une seule fois par processus) : sans ça, Streamlit relance ce
    contrôle à chaque interaction, ce qui ajoute un aller-retour réseau inutile à
    chaque page quand la base est distante (Turso)."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        _migrer_si_besoin(conn)


def _migrer_si_besoin(conn):
    """Ajoute les colonnes apparues après la première version du schéma,
    pour ne pas casser une base de données déjà créée avant leur ajout."""
    colonnes = {row["name"] for row in conn.execute("PRAGMA table_info(cours)").fetchall()}
    if "proprietaire" not in colonnes:
        conn.execute("ALTER TABLE cours ADD COLUMN proprietaire TEXT NOT NULL DEFAULT 'moi'")

    colonnes_documents = {row["name"] for row in conn.execute("PRAGMA table_info(documents)").fetchall()}
    if "categorie" not in colonnes_documents:
        conn.execute("ALTER TABLE documents ADD COLUMN categorie TEXT NOT NULL DEFAULT 'cours'")

    colonnes_questions = {row["name"] for row in conn.execute("PRAGMA table_info(questions)").fetchall()}
    if "type_question" not in colonnes_questions:
        conn.execute("ALTER TABLE questions ADD COLUMN type_question TEXT NOT NULL DEFAULT 'choix_multiple'")
    if "reponse_modele" not in colonnes_questions:
        conn.execute("ALTER TABLE questions ADD COLUMN reponse_modele TEXT")

    colonnes_tentatives = {row["name"] for row in conn.execute("PRAGMA table_info(tentatives)").fetchall()}
    if "details_json" not in colonnes_tentatives:
        conn.execute("ALTER TABLE tentatives ADD COLUMN details_json TEXT")

    colonnes_licences = {row["name"] for row in conn.execute("PRAGMA table_info(licences)").fetchall()}
    if "expire_le" not in colonnes_licences:
        conn.execute("ALTER TABLE licences ADD COLUMN expire_le TEXT")
    if "duree_jours" not in colonnes_licences:
        conn.execute("ALTER TABLE licences ADD COLUMN duree_jours INTEGER NOT NULL DEFAULT 30")
    if "montant" not in colonnes_licences:
        conn.execute("ALTER TABLE licences ADD COLUMN montant REAL")
    if "devise" not in colonnes_licences:
        conn.execute("ALTER TABLE licences ADD COLUMN devise TEXT DEFAULT 'USD'")
    if "contact" not in colonnes_licences:
        conn.execute("ALTER TABLE licences ADD COLUMN contact TEXT")
