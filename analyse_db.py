import sqlite3, json
import os

def analyze_db(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Get list of tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cur.fetchall()]
    summary = {}
    for table in tables:
        # Get column info
        cur.execute(f"PRAGMA table_info({table});")
        cols = cur.fetchall()
        # Look for date-like columns
        date_cols = [col[1] for col in cols if 'date' in col[1].lower()]
        if date_cols:
            table_info = {}
            for dc in date_cols:
                cur.execute(f"SELECT MIN({dc}), MAX({dc}) FROM {table};")
                mn, mx = cur.fetchone()
                table_info[dc] = {'min': mn, 'max': mx}
            summary[table] = table_info
        else:
            # just count rows
            cur.execute(f"SELECT COUNT(*) FROM {table};")
            count = cur.fetchone()[0]
            summary[table] = {'rows': count}
    conn.close()
    return summary

if __name__ == "__main__":
    db_path = os.path.join(os.path.dirname(__file__), "rangewise_market.db")
    info = analyze_db(db_path)
    print(json.dumps(info, indent=2))
