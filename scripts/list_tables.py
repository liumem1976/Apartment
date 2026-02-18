import json
import sqlite3
import sys

if len(sys.argv) < 2:
    print("Usage: list_tables.py <db_path>")
    sys.exit(2)
db = sys.argv[1]
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
rows = [r[0] for r in cur.fetchall()]
print(json.dumps(rows))
