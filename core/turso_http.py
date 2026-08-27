"""Petit client HTTP pour Turso (base de données compatible SQLite, hébergée).

On parle directement à l'API web de Turso (protocole "Hrana sur HTTP") avec la
librairie `requests`, plutôt que d'installer le paquet officiel `libsql` : ce paquet
n'a pas encore de version prête à l'emploi pour les Python très récents sur Windows
(il faudrait compiler du code Rust). Cette approche HTTP fonctionne sur n'importe
quelle version de Python, sans rien installer de compliqué.

Expose une interface volontairement très proche de sqlite3 (cursor/execute/fetchone/
fetchall/lastrowid, commit/close) pour rester compatible avec le reste du code.
"""

import base64

import requests


def _valeur_vers_json(valeur):
    """Convertit une valeur Python en objet JSON typé attendu par l'API Turso."""
    if valeur is None:
        return {"type": "null"}
    if isinstance(valeur, bool):
        return {"type": "integer", "value": str(int(valeur))}
    if isinstance(valeur, int):
        return {"type": "integer", "value": str(valeur)}
    if isinstance(valeur, float):
        return {"type": "float", "value": valeur}
    if isinstance(valeur, (bytes, bytearray)):
        return {"type": "blob", "base64": base64.b64encode(valeur).decode("ascii")}
    return {"type": "text", "value": str(valeur)}


def _valeur_depuis_json(cellule):
    """Convertit une cellule JSON typée renvoyée par Turso en valeur Python normale."""
    type_cellule = cellule.get("type")
    if type_cellule == "null":
        return None
    if type_cellule == "integer":
        return int(cellule["value"])
    if type_cellule == "float":
        return cellule["value"]
    if type_cellule == "text":
        return cellule["value"]
    if type_cellule == "blob":
        return base64.b64decode(cellule["base64"])
    return None


class TursoHTTPCursor:
    def __init__(self, connexion):
        self._connexion = connexion
        self.description = None
        self.lastrowid = None
        self._dernier_resultat = None

    def execute(self, sql, params=()):
        args = [_valeur_vers_json(p) for p in params]
        payload = {
            "requests": [
                {"type": "execute", "stmt": {"sql": sql, "args": args}},
                {"type": "close"},
            ]
        }
        reponse = requests.post(
            f"{self._connexion.url}/v2/pipeline",
            json=payload,
            headers=self._connexion.headers,
            timeout=20,
        )
        reponse.raise_for_status()
        data = reponse.json()

        resultat = None
        for r in data.get("results", []):
            if r.get("type") == "error":
                message = r.get("error", {}).get("message", "Erreur Turso inconnue")
                raise RuntimeError(f"Erreur Turso : {message}")
            reponse_r = r.get("response") or {}
            if reponse_r.get("type") == "execute":
                resultat = reponse_r.get("result")

        self._dernier_resultat = resultat
        if resultat:
            self.description = [(c.get("name"),) for c in resultat.get("cols", [])]
            lir = resultat.get("last_insert_rowid")
            self.lastrowid = int(lir) if lir else None
        else:
            self.description = None
            self.lastrowid = None
        return self

    def fetchall(self):
        if not self._dernier_resultat:
            return []
        return [
            tuple(_valeur_depuis_json(v) for v in ligne)
            for ligne in self._dernier_resultat.get("rows", [])
        ]

    def fetchone(self):
        lignes = self.fetchall()
        return lignes[0] if lignes else None


class TursoHTTPConnection:
    """Connexion factice : chaque exécution est une requête HTTP indépendante et déjà
    validée côté serveur (pas besoin d'un vrai commit/rollback pour notre usage)."""

    def __init__(self, url: str, auth_token: str):
        self.url = url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }

    def cursor(self):
        return TursoHTTPCursor(self)

    def commit(self):
        pass  # chaque requête est déjà appliquée côté serveur

    def close(self):
        pass  # rien à fermer, ce n'est qu'un client HTTP sans état
