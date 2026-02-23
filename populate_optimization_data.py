import sqlite3
import time

def populate():
    conn = sqlite3.connect('tennis_data.db')
    c = conn.cursor()
    
    print("Populating optimization data...")
    
    # 1. Update scout_category
    print("  Categorizing players (Junior)...")
    junior_where = """( 
        (age IS NOT NULL AND age <= 18) OR 
        (age_group IS NOT NULL AND (age_group LIKE 'U%' OR age_group LIKE '1_-1_' OR age_group LIKE '%Junior%')) OR
        (age IS NULL AND age_group IS NULL AND (
            (gender = 'F' AND utr_singles < 11.5) OR
            (gender = 'M' AND utr_singles < 13.5) OR
            (gender IS NULL AND utr_singles < 13.0)
        ))
    ) AND (college IS NULL OR college = '-' OR college LIKE '%Recruiting%')"""
    c.execute(f"UPDATE players SET scout_category = 'junior' WHERE {junior_where}")
    conn.commit()
    
    print("  Categorizing players (College)...")
    c.execute("UPDATE players SET scout_category = 'college' WHERE is_active_college = 1")
    conn.commit()
    
    print("  Categorizing players (Adult)...")
    adult_where = """(
        (age IS NOT NULL AND age > 18) OR 
        (age IS NULL AND (
            age_group IS NULL OR (
                age_group NOT LIKE 'U%' AND 
                age_group NOT LIKE '1_-1_' AND 
                age_group NOT LIKE '%Junior%'
            )
        ))
    ) AND (is_active_college = 0 OR is_active_college IS NULL) AND scout_category IS NULL"""
    c.execute(f"UPDATE players SET scout_category = 'adult' WHERE {adult_where}")
    conn.commit()

    # 2. Update match statistics
    print("  Calculating match stats (this may take a while for 13M matches)...")
    start_time = time.time()
    
    # Create a temporary table for counts to avoid a billion subqueries
    c.execute("DROP TABLE IF EXISTS temp_match_stats")
    c.execute("""
        CREATE TABLE temp_match_stats AS
        SELECT player_id, COUNT(*) as cnt, MAX(date) as last_date
        FROM (
            SELECT winner_id as player_id, date FROM matches
            UNION ALL
            SELECT loser_id as player_id, date FROM matches
        )
        GROUP BY player_id
    """)
    c.execute("CREATE INDEX idx_temp_stats_pid ON temp_match_stats(player_id)")
    conn.commit()
    
    print(f"  Aggregated stats in {time.time() - start_time:.2f}s. Updating players table...")
    
    c.execute("""
        UPDATE players
        SET match_count = COALESCE((SELECT cnt FROM temp_match_stats WHERE temp_match_stats.player_id = players.player_id), 0),
            latest_match_date = (SELECT last_date FROM temp_match_stats WHERE temp_match_stats.player_id = players.player_id)
    """)
    conn.commit()
    
    print(f"  Population complete in {time.time() - start_time:.2f}s.")
    
    c.execute("DROP TABLE temp_match_stats")
    conn.close()

if __name__ == "__main__":
    populate()
