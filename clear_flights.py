import sqlite3, pathlib, sys

# Path to the SQLite DB (relative to this script)
db_path = pathlib.Path(__file__).resolve().parents[0] / "Data_load" / "flight.db"

if not db_path.exists():
    print(f"Database not found at {db_path}")
    sys.exit(1)

conn = sqlite3.connect(db_path)
conn.execute("DELETE FROM flights")
conn.commit()
conn.close()
print("All rows deleted from flights table.")
