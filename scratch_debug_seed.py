import sys
sys.path.insert(0, ".")
from core.auth import _identifiant
from core.db import get_connection
from core import repository

ident = _identifiant("DebugQA2", "debugpass456")
print("identifiant:", ident)

with get_connection() as conn:
    cours = conn.execute("SELECT id FROM cours WHERE proprietaire = ?", (ident,)).fetchall()
    print("cours:", cours)
