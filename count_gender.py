import sqlite3
conn = sqlite3.connect('tennis_data.db')
c = conn.cursor()
c.execute("SELECT gender, COUNT(*) FROM players WHERE player_id LIKE 'sackmann_%' GROUP BY gender")
for row in c.fetchall():
    print(row)
conn.close()
