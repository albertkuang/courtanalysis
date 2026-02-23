import sqlite3
import time

def add_indexes():
    conn = sqlite3.connect('tennis_data.db')
    c = conn.cursor()
    
    start_time = time.time()
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_matches_winner ON matches(winner_id)",
        "CREATE INDEX IF NOT EXISTS idx_matches_loser ON matches(loser_id)",
        "CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date)",
        "CREATE INDEX IF NOT EXISTS idx_matches_level ON matches(tourney_level)",
        "CREATE INDEX IF NOT EXISTS idx_rankings_pid_date ON rankings(player_id, date)",
        "CREATE INDEX IF NOT EXISTS idx_players_birthdate ON players(birth_date)"
    ]
    
    print("=== Adding Indexes ===")
    for idx_sql in indexes:
        print(f"Executing: {idx_sql}")
        try:
            c.execute(idx_sql)
            conn.commit()
            print("  -> Done")
        except Exception as e:
            print(f"  -> Error: {e}")
            
    end_time = time.time()
    print(f"\nIndexes added in {end_time - start_time:.2f} seconds.")
    conn.close()

if __name__ == "__main__":
    add_indexes()
