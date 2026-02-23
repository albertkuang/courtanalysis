import sqlite3

def update_junior_finalists_stats():
    db_file = 'tennis_data.db'
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    print("Updating winner stats...")
    cursor.execute("""
        UPDATE junior_finalists
        SET winner_utr = (SELECT utr_singles FROM players WHERE players.player_id = junior_finalists.winner_id),
            winner_rank = (SELECT pro_rank FROM players WHERE players.player_id = junior_finalists.winner_id)
        WHERE EXISTS (SELECT 1 FROM players WHERE players.player_id = junior_finalists.winner_id)
    """)
    
    print("Updating finalist stats...")
    cursor.execute("""
        UPDATE junior_finalists
        SET finalist_utr = (SELECT utr_singles FROM players WHERE players.player_id = junior_finalists.finalist_id),
            finalist_rank = (SELECT pro_rank FROM players WHERE players.player_id = junior_finalists.finalist_id)
        WHERE EXISTS (SELECT 1 FROM players WHERE players.player_id = junior_finalists.finalist_id)
    """)
    
    conn.commit()
    conn.close()
    print("Stats update complete.")

if __name__ == "__main__":
    update_junior_finalists_stats()
