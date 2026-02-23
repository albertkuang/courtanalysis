import sqlite3
import time

def migrate():
    conn = sqlite3.connect('tennis_data.db')
    c = conn.cursor()
    
    print("Migrating database for performance optimization...")
    
    # 1. Add Columns to players table
    c.execute("PRAGMA table_info(players)")
    columns = [row[1] for row in c.fetchall()]
    
    if 'scout_category' not in columns:
        print("  Adding 'scout_category' column...")
        c.execute("ALTER TABLE players ADD COLUMN scout_category TEXT")
        
    if 'match_count' not in columns:
        print("  Adding 'match_count' column...")
        c.execute("ALTER TABLE players ADD COLUMN match_count INTEGER DEFAULT 0")
        
    if 'latest_match_date' not in columns:
        print("  Adding 'latest_match_date' column...")
        c.execute("ALTER TABLE players ADD COLUMN latest_match_date TEXT")
        
    conn.commit()
    
    # 2. Add Indexes
    print("  Creating indexes (this may take a few minutes for 13M matches)...")
    
    # Player category indexes
    c.execute("CREATE INDEX IF NOT EXISTS idx_players_scout_category ON players(scout_category)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_players_active_college ON players(is_active_college)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_players_country_gender ON players(country, gender)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_players_utr_singles_desc ON players(utr_singles DESC)")
    
    # Match performance indexes (Double check existing ones)
    c.execute("CREATE INDEX IF NOT EXISTS idx_matches_winner_date ON matches(winner_id, date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_matches_loser_date ON matches(loser_id, date)")
    
    conn.commit()
    print("Migration complete.")
    conn.close()

if __name__ == "__main__":
    migrate()
