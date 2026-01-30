
import sqlite3
import re
from datetime import datetime, timedelta
import tennis_db

def get_db_connection():
    return sqlite3.connect('tennis_data.db')

def refresh_stats():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    print("Fetching all players...")
    c.execute("SELECT player_id, name, utr_singles FROM players")
    players = [dict(row) for row in c.fetchall()]
    
    print(f"Processing {len(players)} players...")
    
    updated_count = 0
    
    # Pre-fetch all history to minimize queries? No, memory usage.
    # Just do per-player queries, it's sqlite local file, fast enough for 1000 players.
    
    for i, p in enumerate(players):
        pid = p['player_id']
        name = p['name']
        current_utr = p['utr_singles'] or 0
        
        # 1. Calculate Match Stats
        # Get matches where this player played
        matches = tennis_db.get_player_matches(conn, pid)
        
        comeback_wins = 0
        tiebreak_wins = 0
        tiebreak_losses = 0
        three_set_wins = 0
        three_set_losses = 0
        
        one_year_ago_date = datetime.now() - timedelta(days=365)
        
        for m in matches:
            # Date Filter
            m_date_str = m.get('date')
            if not m_date_str: continue
            
            try:
                # Handle varying ISO formats (with/without Z, fractional seconds)
                # Simple truncation to 19 chars (YYYY-MM-DDTHH:MM:SS) usually works for comparison if ISO
                # Or parsing
                m_date_clean = m_date_str.replace('Z', '').split('.')[0]
                m_date = datetime.fromisoformat(m_date_clean)
                
                if m_date < one_year_ago_date:
                    continue
            except:
                continue

            score = m.get('score', '')
            if not score: continue
            
            # Normalize score string
            sets = score.strip().split(' ')
            if not sets: continue
            
            # Determine if player was winner of the MATCH
            # matches returned by get_player_matches has winner_id, loser_id
            is_match_winner = str(m['winner_id']) == str(pid)
            
            # 3-Set Check
            # Assuming best of 3. If 3 sets, it's a 3-setter.
            # Some matches might be best of 5 (Grand Slams), but rare in this dataset (juniors/college)
            # Safe heuristic: if 3 sets played, count it.
            if len(sets) >= 3:
                # Exclude if it's a retirement/walkover? 
                # Score usually handles that, but "6-4 2-0 RET" is 2 sets.
                # Assuming valid completed sets format roughly "d-d"
                valid_sets = [s for s in sets if re.match(r'\d+-\d+', s)]
                if len(valid_sets) >= 3:
                    if is_match_winner:
                        three_set_wins += 1
                    else:
                        three_set_losses += 1

            # Tiebreak & Comeback Check
            for idx, s in enumerate(sets):
                match = re.match(r'(\d+)-(\d+)', s)
                if match:
                    w_games = int(match.group(1)) # Match Winner's games
                    l_games = int(match.group(2)) # Match Loser's games
                    
                    # Tiebreak (6-7 or 7-6)
                    # Also 7-5 is NOT a tiebreak.
                    # 10-point tiebreaks in lieu of 3rd set often coded as "1-0" or "10-5"
                    # But strictly 7-6 or 6-7 is a set tiebreak.
                    is_tb = (w_games == 7 and l_games == 6) or (w_games == 6 and l_games == 7)
                    
                    if is_tb:
                        if is_match_winner:
                            # Match Winner vs Metric
                            # If w_games > l_games (7-6), Match Winner WON TB
                            if w_games > l_games:
                                tiebreak_wins += 1
                            else:
                                tiebreak_losses += 1
                        else:
                            # Player is Match Loser
                            # If Match Winner WON TB (7-6), Player LOST TB
                            if w_games > l_games:
                                tiebreak_losses += 1
                            else:
                                tiebreak_wins += 1
                    
                    # Comeback Logic (Winner Only)
                    if is_match_winner and idx == 0:
                        # If Match Winner lost first set
                        # w_games < l_games (e.g. 4-6)
                        if w_games < l_games:
                            comeback_wins += 1
                            
        # 2. Calculate Year Delta
        year_delta = 0.0
        try:
            c.execute("SELECT date, rating FROM utr_history WHERE player_id = ? ORDER BY date ASC", (pid,))
            history = c.fetchall()
            
            if history and current_utr > 0:
                one_year_ago = datetime.now() - timedelta(days=365)
                prior_rating = None
                closest_diff_seconds = float('inf')
                
                for h in history:
                    # Date format varies: "2023-01-01T00:00:00Z" or similar
                    d_str = h['date']
                    try:
                        # Handle potential Z or no Z
                        d_str_clean = d_str.replace('Z', '')
                        # Truncate fractional seconds if present
                        d_str_clean = d_str_clean.split('.')[0]
                        
                        h_date = datetime.fromisoformat(d_str_clean)
                        
                        # Find entry roughly 1 year ago
                        diff = abs((h_date - one_year_ago).total_seconds())
                        
                        # Allow window? Just pick closest to 1 year ago
                        if diff < closest_diff_seconds:
                            closest_diff_seconds = diff
                            prior_rating = h['rating']
                    except:
                        continue
                
                # Check if "closest" is actually reasonable (e.g. within a month of 1 year ago)
                # 30 days = 2592000 seconds
                if prior_rating and closest_diff_seconds < (60 * 60 * 24 * 60): # Relaxed to 2 months for better hits
                    year_delta = current_utr - prior_rating
        except Exception as e:
            # print(f"Error delta for {pid}: {e}")
            pass
            
        # 3. Update DB
        try:
            c.execute("""
                UPDATE players 
                SET comeback_wins = ?, 
                    year_delta = ?, 
                    tiebreak_wins = ?, 
                    tiebreak_losses = ?,
                    three_set_wins = ?,
                    three_set_losses = ?
                WHERE player_id = ?
            """, (comeback_wins, year_delta, tiebreak_wins, tiebreak_losses, three_set_wins, three_set_losses, pid))
            updated_count += 1
        except Exception as e:
            print(f"Failed to update {name}: {e}")
            
        if i % 100 == 0:
            print(f"  Processed {i}...")
            conn.commit()
            
    conn.commit()
    conn.close()
    print(f"Done. Updated {updated_count} players.")

if __name__ == "__main__":
    refresh_stats()
