
def get_match_stats(conn, player_id, year=None):
    """
    Get aggregated match stats for a player (Wins, Losses, Aces, DFs).
    Efficiently sums stats using SQL.
    """
    c = conn.cursor()
    
    # Base query
    query = """
        SELECT 
            SUM(CASE WHEN winner_id = ? THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN loser_id = ? THEN 1 ELSE 0 END) as losses,
            SUM(CASE WHEN winner_id = ? THEN w_ace ELSE l_ace END) as total_aces,
            SUM(CASE WHEN winner_id = ? THEN w_df ELSE l_df END) as total_dfs
        FROM matches 
        WHERE (winner_id = ? OR loser_id = ?)
    """
    params = [player_id, player_id, player_id, player_id, player_id, player_id]
    
    # Year filter
    if year:
        query += " AND date LIKE ?"
        params.append(f"{year}%")
        
    c.execute(query, params)
    row = c.fetchone()
    
    if row:
        return {
            "wins": row[0] or 0,
            "losses": row[1] or 0,
            "total_aces": row[2] or 0,
            "total_dfs": row[3] or 0
        }
    return {"wins": 0, "losses": 0, "total_aces": 0, "total_dfs": 0}
