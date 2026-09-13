"""Inspection rapide (jetable) du contenu d'une base DRENAET-RH."""
import sqlite3
import sys
from pathlib import Path

chemin = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/drenaet.db")
print(f"Base : {chemin}  ({chemin.stat().st_size} octets)")

cx = sqlite3.connect(str(chemin))
tables = [r[0] for r in cx.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()]
print(f"Tables ({len(tables)}) : {', '.join(tables)}")

for table in ("utilisateurs", "personnel", "structures", "settings"):
    if table in tables:
        n = cx.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:<14} : {n} ligne(s)")
cx.close()
