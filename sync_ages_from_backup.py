
import sqlite3
import os

DB_MAIN = r'C:\work\github\courtanalysis\tennis_data.db'
DB_SOURCE = r'C:\work\github\courtanalysis\bck\tennis_data.db'

def sync_ages():
    if not os.path.exists(DB_SOURCE):
        print(f"Error: Source database not found at {DB_SOURCE}")
        return

    print(f"Connecting to {DB_MAIN}...")
    conn = sqlite3.connect(DB_MAIN)
    cursor = conn.cursor()

    try:
        # Attach the source database
        print(f"Attaching {DB_SOURCE}...")
        cursor.execute(f"ATTACH DATABASE '{DB_SOURCE}' AS source_db")
        
        # Check if UPDATE FROM is supported (SQLite 3.33+)
        # We can try to execute it.
        print("Attempting bulk UPDATE from source database...")
        
        # Check which columns we want to sync
        # We want age, birth_date, maybe age_group?
        cursor.execute("""
            UPDATE players
            SET age = src.age,
                birth_date = src.birth_date,
                age_group = src.age_group
            FROM source_db.players AS src
            WHERE players.player_id = src.player_id
              AND src.age IS NOT NULL
        """)
        
        print(f"Updated {cursor.rowcount} players with age info.")
        conn.commit()

    except sqlite3.OperationalError as e:
        if "near \"FROM\": syntax error" in str(e):
            print("UPDATE FROM not supported (older SQLite). Switching to Python iteration...")
            conn.rollback()
            # fallback
            sync_ages_manual(conn)
        else:
            print(f"Operational failed: {e}")
            conn.rollback()
    except Exception as e2:
        print(f"An error occurred: {e2}")
        conn.rollback()
    finally:
        conn.close()

def sync_ages_manual(conn):
    # Retrieve data from source
    # Cannot use 'source_db' alias easily if we detached or errors? 
    # Actually connection is same.
    cursor = conn.cursor()
    print("Fetching age data from source...")
    cursor.execute("SELECT player_id, age, birth_date, age_group FROM source_db.players WHERE age IS NOT NULL")
    source_data = cursor.fetchall()
    
    print(f"Found {len(source_data)} players with age in source.")
    
    print("Updating main database...")
    count = 0
    batch_size = 1000
    
    # helper for update
    sql = "UPDATE players SET age = ?, birth_date = ?, age_group = ? WHERE player_id = ?"
    
    batch = []
    for row in source_data:
        # row: pid, age, dob, group
        # params: age, dob, group, pid
        batch.append((row[1], row[2], row[3], row[0]))
        
        if len(batch) >= batch_size:
            cursor.executemany(sql, batch)
            conn.commit()
            count += len(batch)
            batch = []
            print(f"Updated {count}...")
            
    if batch:
        cursor.executemany(sql, batch)
        conn.commit()
        count += len(batch)
        
    print(f"Manual sync complete. Updated {count} players.")

if __name__ == "__main__":
    sync_ages()
