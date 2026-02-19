import sqlite3
import sys


def check(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT unit_id, kind, slot, COUNT(*) AS c FROM meter GROUP BY unit_id, kind, slot HAVING c > 1;"
        )
    except Exception as e:
        print("ERROR_SQL:", e)
        return 2
    rows = cur.fetchall()
    if not rows:
        print("NO_DUPLICATES")
        return 0
    print("DUPLICATES_FOUND")
    for r in rows:
        print(r)
    return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_duplicate_meters.py <path_to_sqlite_db>")
        sys.exit(3)
    db = sys.argv[1]
    sys.exit(check(db))
