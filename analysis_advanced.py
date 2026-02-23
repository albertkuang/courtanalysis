import math
import sqlite3
import tennis_abstract_scraper
from datetime import datetime

def get_db_connection():
    conn = sqlite3.connect('tennis_data.db')
    conn.row_factory = sqlite3.Row
    return conn

def predict_match_outcome(player1_id, player2_id, use_live_elo=False):
    """
    Predict match outcome based on UTR (and Elo if available).
    Returns dict with win probabilities.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    # Fetch players
    c.execute("SELECT * FROM players WHERE player_id IN (?, ?)", (str(player1_id), str(player2_id)))
    players = {str(row['player_id']): dict(row) for row in c.fetchall()}
    conn.close()
    
    p1 = players.get(str(player1_id))
    p2 = players.get(str(player2_id))
    
    if not p1 or not p2:
        return {'error': 'Player not found'}
        
    # 1. UTR Prediction
    utr1 = p1.get('utr_singles') or 0
    utr2 = p2.get('utr_singles') or 0
    
    utr_diff = utr1 - utr2
    # Simple logistic function approximation for UTR
    k = 1.5 
    utr_prob = 1 / (1 + math.exp(-k * utr_diff))
    
    # 2. Tennis Abstract Elo (Optional)
    elo_prob = None
    elo1, elo2 = None, None
    if use_live_elo:
        try:
            # Attempt to fetch live Elo
            # Use gender from DB if available, default to F
            g1 = p1.get('gender', 'F')
            # Scrape profiles (might be slow)
            d1 = tennis_abstract_scraper.scrape_player(p1['name'], gender=g1)
            d2 = tennis_abstract_scraper.scrape_player(p2['name'], gender=g1) # Assume same gender
            
            if d1 and d2:
                elo1 = d1.get('eloRating')
                elo2 = d2.get('eloRating')
                
                if elo1 and elo2:
                    # Elo formula: 1 / (1 + 10^((r2-r1)/400))
                    elo_diff = elo1 - elo2
                    elo_prob = 1 / (1 + 10 ** (-elo_diff / 400))
        except Exception as e:
            print(f"Elo fetch failed: {e}")

    # Combine or return details
    result = {
        'player1': {
            'name': p1['name'],
            'utr': utr1,
            'win_probability': round(utr_prob * 100, 1)
        },
        'player2': {
            'name': p2['name'],
            'utr': utr2,
            'win_probability': round((1 - utr_prob) * 100, 1)
        },
        'model': 'UTR Logistic Regression (k=1.5)'
    }
    
    if elo_prob is not None:
        result['elo_prediction'] = {
            'player1_elo': elo1,
            'player2_elo': elo2,
            'player1_win_prob': round(elo_prob * 100, 1)
        }
        
    return result

def get_match_charting(match_id):
    """
    Get shot-by-shot or summary stats for a charted match.
    Uses local CSV cache of Match Charting Project data.
    """
    # Attempt to guess gender from match ID or try both
    # ID format often has gender indicator? e.g. 20251214-W-...
    gender = 'F'
    if '-M-' in match_id:
        gender = 'M'
        
    points = tennis_abstract_scraper.get_match_points(match_id, gender)
    
    if points:
        return {
            'match_id': match_id, 
            'points_count': len(points),
            'points': points
        }
    else:
        return {
            "error": "Match points not found (or download failed).",
            "url": f"https://www.tennisabstract.com/charting/{match_id}.html"
        }

def fetch_player_charting_overview(player_name, gender='F'):
    """
    Wrapper for tennis_abstract_scraper data
    """
    try:
        stats = tennis_abstract_scraper.fetch_player_charting_stats(player_name, gender)
        matches = tennis_abstract_scraper.fetch_player_charted_matches(player_name, gender, limit=10)
        return {
            'stats': stats,
            'matches': matches
        }
    except Exception as e:
        return {'error': str(e)}
