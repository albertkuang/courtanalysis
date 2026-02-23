
import os

api_file = 'api.py'

with open(api_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Target Function content to replace
orig_func = """@app.get("/players/{player_id}/matches")
def get_player_matches(
    player_id: str,
    year: str = Query(None, description="Filter by year (e.g., '2024')"),
    limit: int = Query(100, ge=1, le=500, description="Number of matches to return"),
    offset: int = Query(0, ge=0, description="Number of matches to skip")
):
    conn = get_db_connection()
    # Get paginated matches with optional year filter
    matches = tennis_db.get_player_matches(conn, player_id, year=year, limit=limit, offset=offset)
    # Get total count for pagination info
    total_count = tennis_db.get_player_matches_count(conn, player_id, year=year)
    # Get available years for this player
    available_years = tennis_db.get_player_match_years(conn, player_id)
    conn.close()
    return {
        "count": len(matches),
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "available_years": available_years,
        "data": matches
    }"""

new_func = """@app.get("/players/{player_id}/matches")
def get_player_matches(
    player_id: str,
    year: str = Query(None, description="Filter by year (e.g., '2024')"),
    limit: int = Query(100, ge=1, le=500, description="Number of matches to return"),
    offset: int = Query(0, ge=0, description="Number of matches to skip")
):
    conn = get_db_connection()
    # Get paginated matches with optional year filter
    matches = tennis_db.get_player_matches(conn, player_id, year=year, limit=limit, offset=offset)
    # Get total count for pagination info
    total_count = tennis_db.get_player_matches_count(conn, player_id, year=year)
    # Get available years for this player
    available_years = tennis_db.get_player_match_years(conn, player_id)
    
    # Get aggregated stats
    try:
        stats = tennis_db.get_match_stats(conn, player_id, year=year)
    except Exception as e:
        print(f"Error fetching stats: {e}")
        stats = {"wins": 0, "losses": 0, "total_aces": 0, "total_dfs": 0}
        
    conn.close()
    return {
        "count": len(matches),
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "available_years": available_years,
        "stats": stats,
        "data": matches
    }"""

if orig_func in content:
    content = content.replace(orig_func, new_func)
    print("Replaced get_player_matches endpoint")
    with open(api_file, 'w', encoding='utf-8') as f:
        f.write(content)
else:
    print("Could not find get_player_matches endpoint string")
    # Debug: print what we are looking for vs what we might have
    # print(orig_func[:100])
