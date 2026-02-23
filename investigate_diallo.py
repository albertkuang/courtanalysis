import sqlite3

conn = sqlite3.connect('tennis_data.db')
c = conn.cursor()

# 1. Find Gabriel Diallo in players table
print("=== Players named Diallo ===")
c.execute("SELECT player_id, name, country FROM players WHERE name LIKE '%Diallo%'")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]} ({r[2]})")

# 2. Find in sackmann_profiles
print("\n=== Sackmann profiles named Diallo ===")
c.execute("SELECT sackmann_id, full_name FROM sackmann_profiles WHERE full_name LIKE '%Diallo%'")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")

# 3. Check rankings for Gabriel Diallo
print("\n=== Rankings with 'Diallo' in player_id ===")
c.execute("SELECT DISTINCT player_id FROM rankings WHERE player_id LIKE '%diallo%' OR player_id LIKE '%Diallo%' LIMIT 5")
for r in c.fetchall():
    print(f"  {r[0]}")

# 4. Check what player_ids look like in rankings table
print("\n=== Sample ranking player_ids (ATP) ===")
c.execute("SELECT DISTINCT player_id FROM rankings WHERE player_id LIKE 'atp_%' LIMIT 5")
for r in c.fetchall():
    print(f"  {r[0]}")

# 5. Check Gabriel Diallo by numeric ID if we can find it
c.execute("SELECT sackmann_id FROM sackmann_profiles WHERE full_name LIKE '%Gabriel%Diallo%'")
diallo_id = c.fetchone()
if diallo_id:
    print(f"\n=== Gabriel Diallo's Sackmann ID: {diallo_id[0]} ===")
    # Check rankings with this ID
    c.execute("SELECT date, rank, points FROM rankings WHERE player_id = ? ORDER BY date DESC LIMIT 5", (f"atp_{diallo_id[0]}",))
    rows = c.fetchall()
    print(f"Rankings for atp_{diallo_id[0]}:")
    for r in rows:
        print(f"  {r[0]}: Rank {r[1]}")

conn.close()
