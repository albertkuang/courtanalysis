import sqlite3
import time

DB_PATH = "tennis_data.db"

try:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT tournament, tourney_level FROM matches LIMIT 20")
    print(c.fetchall())
    conn.close()
except Exception as e:
    print(e)
