import sqlite3
import pandas as pd

conn = sqlite3.connect('tennis_data.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print("Tables:", [row[0] for row in cursor.fetchall()])
conn.close()
