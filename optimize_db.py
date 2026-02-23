import sqlite3
import os
import time

DB_PATH = 'tennis_data.db'

def optimize():
    print(f"Optimizing {DB_PATH}... (File size: {os.path.getsize(DB_PATH)/1024/1024/1024:.2f} GB)")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. PRAGMA Settings for Session
    print("Setting performance PRAGMAs...")
    c.execute("PRAGMA journal_mode = WAL;")
    c.execute("PRAGMA synchronous = NORMAL;")
    c.execute("PRAGMA cache_size = -512000;") # 512MB cache
    c.execute("PRAGMA mmap_size = 3000000000;") # 3GB MMAP
    c.execute("PRAGMA temp_store = MEMORY;")
    
    # 2. Add Missing Indexes
    print("Creating indexes... this may take a while for 14M rows...")
    
    index_start = time.time()
    
    # Players name index for searches
    print("  Index: players.name")
    c.execute("CREATE INDEX IF NOT EXISTS idx_players_name ON players (name);")
    
    # Composite Index for Scout view filtering and sorting
    print("  Index: players scout optimization (scout_category, country, gender, utr_singles)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_players_scout_composite ON players (scout_category, country, gender, utr_singles DESC);")
    
    # Match History Optimization (often filtered by player and sorted by date)
    # idx_matches_winner_date and idx_matches_loser_date already exist partly? 
    # Let's ensure they are optimal
    print("  Ensuring match history indexes...")
    c.execute("CREATE INDEX IF NOT EXISTS idx_matches_winner_date ON matches (winner_id, date DESC);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_matches_loser_date ON matches (loser_id, date DESC);")
    
    # Rankings Optimization
    print("  Index: rankings.player_id_date")
    c.execute("CREATE INDEX IF NOT EXISTS idx_rankings_pid_date ON rankings (player_id, date DESC);")
    
    print(f"Index creation completed in {time.time() - index_start:.2f}s")
    
    # 3. Analyze for Query Planner optimization
    print("Running ANALYZE to update statistics... (Crucial for large DBs)")
    start_analyze = time.time()
    c.execute("ANALYZE;")
    print(f"ANALYZE completed in {time.time() - start_analyze:.2f}s")
    
    conn.commit()
    conn.close()
    print("\nOptimization Complete.")

if __name__ == "__main__":
    optimize()
