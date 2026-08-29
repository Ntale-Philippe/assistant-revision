import sys
sys.path.insert(0, ".")
from core.db import get_connection

with get_connection() as conn:
    print("--- quiz types existants ---")
    print(conn.execute("SELECT type, COUNT(*) as n FROM quiz GROUP BY type").fetchall())
    print("--- syntheses count ---")
    print(conn.execute("SELECT COUNT(*) as n FROM syntheses").fetchall())
    print("--- messages_chat count ---")
    print(conn.execute("SELECT COUNT(*) as n FROM messages_chat").fetchall())
    print("--- profils count ---")
    print(conn.execute("SELECT COUNT(*) as n FROM profils").fetchall())
    print("--- premium rows ---")
    print(conn.execute("SELECT COUNT(*) as n FROM premium").fetchall())
