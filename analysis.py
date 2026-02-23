import sqlite3
from datetime import datetime, timedelta
import numpy as np
import advanced_stats

def get_quarterly_progress(player_id: str):
    """
    Calculate progress over the last Quarter (90 Days).
    Returns: {
        'current_utr': float,
        'past_utr': float,
        'utr_delta': float,
        'current_win_rate': float (Last 20 Matches),
        'past_win_rate': float (Win Rate snapshot from 90 days ago),
        'volume': int (matches in last 90 days),
        'volume_prev': int (matches in 90-180 days ago)
    }
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Dates
    now = datetime.now()
    d_90_ago = now - timedelta(days=90)
    d_180_ago = now - timedelta(days=180)
    d_90_str = d_90_ago.strftime('%Y-%m-%d')
    d_180_str = d_180_ago.strftime('%Y-%m-%d')
    
    # 2. Match Volume
    # Last 90 Days
    c.execute("""
        SELECT COUNT(*) as count FROM matches 
        WHERE (winner_id = ? OR loser_id = ?) 
        AND date >= ?
    """, (player_id, player_id, d_90_str))
    volume = c.fetchone()['count']
    
    # Previous 90 Days (90-180)
    c.execute("""
        SELECT COUNT(*) as count FROM matches 
        WHERE (winner_id = ? OR loser_id = ?) 
        AND date < ? AND date >= ?
    """, (player_id, player_id, d_90_str, d_180_str))
    volume_prev = c.fetchone()['count']
    
    # 3. UTR Progress
    # Get Current UTR (from players table)
    c.execute("SELECT utr_singles FROM players WHERE player_id = ?", (player_id,))
    p = c.fetchone()
    current_utr = p['utr_singles'] if p else None
    
    # Get Past UTR (from utr_history nearest to 90 days ago)
    # We look for a record closest to d_90_ago
    c.execute("""
        SELECT rating FROM utr_history 
        WHERE player_id = ? 
        AND date <= ? 
        ORDER BY date DESC 
        LIMIT 1
    """, (player_id, d_90_str))
    h = c.fetchone()
    past_utr = h['rating'] if h else None
    
    # If no history exactly then, maybe try match loser_utr/winner_utr from that time?
    # For now, fallback to current if missing (delta 0)
    if past_utr is None and current_utr is not None:
        pass # past_utr stays None
        
    utr_delta = round(current_utr - past_utr, 2) if (current_utr and past_utr) else 0.0

    # 4. Win Rate Snapshot
    # Current Win Rate (Last 20 Matches)
    # We can reuse logic or just calc here
    def get_win_rate_at_date(pid, date_limit_str=None):
        # Fetch last 20 matches BEFORE date_limit
        query = "SELECT winner_id FROM matches WHERE (winner_id = ? OR loser_id = ?)"
        params = [pid, pid]
        if date_limit_str:
            query += " AND date <= ?"
            params.append(date_limit_str)
            
        query += " ORDER BY date DESC LIMIT 20"
        
        c.execute(query, tuple(params))
        rows = c.fetchall()
        if not rows: return 0.0
        
        wins = sum(1 for r in rows if str(r['winner_id']) == str(pid))
        return round((wins / len(rows)) * 100, 1)

    current_win_rate = get_win_rate_at_date(player_id)
    past_win_rate = get_win_rate_at_date(player_id, d_90_str)

    conn.close()
    
    return {
        'period': f"Last 3 Months ({d_90_str} to Now)",
        'current_utr': current_utr,
        'past_utr': round(past_utr or 0, 2),
        'utr_delta': utr_delta,
        'current_win_rate': current_win_rate,
        'past_win_rate': past_win_rate,
        'win_rate_delta': round(current_win_rate - past_win_rate, 1),
        'volume': volume,
        'volume_prev': volume_prev,
        'volume_delta': volume - volume_prev
    }



def get_db_connection():
    conn = sqlite3.connect('tennis_data.db')
    conn.row_factory = sqlite3.Row
    return conn

# ... (Previous functions same)

def analyze_age_cohort(player_data):
    """
    Compare player to their age cohort.
    Only applies if age is known.
    """
    age = player_data.get('age')
    if not age or age < 10 or age > 22: # Focus on Junior/College age
        return None
        
    conn = get_db_connection()
    c = conn.cursor()
    # Get all players of same age (gender specific if needed, usually yes)
    gender = player_data.get('gender')
    
    # 1. Get Aggregates
    query = "SELECT AVG(utr_singles) as avg_utr, MAX(utr_singles) as max_utr, COUNT(*) as total FROM players WHERE age = ? AND utr_singles > 0"
    params = [age]
    
    if gender:
        query += " AND gender = ?"
        params.append(gender)
        
    c.execute(query, tuple(params))
    stats = c.fetchone()
    
    if not stats or stats['total'] == 0:
        conn.close()
        return None
        
    my_utr = player_data.get('utr_singles') or 0
    avg_utr = stats['avg_utr']
    max_utr = stats['max_utr']
    total_peers = stats['total']
    
    # 2. Calculate Percentile (Rank)
    # How many are BELOW me?
    # Percentile = (Count < MyUTR) / Total * 100
    
    query2 = "SELECT COUNT(*) as lower_count FROM players WHERE age = ? AND utr_singles > 0 AND utr_singles < ?"
    params2 = [age, my_utr]
    if gender:
        query2 += " AND gender = ?"
        params2.append(gender)
        
    c.execute(query2, tuple(params2))
    lower_count = c.fetchone()['lower_count']
    
    conn.close()
    
    percentile = (lower_count / total_peers) * 100
    
    return {
        'cohort_avg': round(avg_utr, 2),
        'cohort_max': round(max_utr, 2),
        'percentile': round(percentile, 1),
        'total_peers': total_peers
    }

def find_similar_players(player_data):
    """
    Find 'Nearest Neighbors': Current players with similar profile.
    Criteria:
    - Same Gender
    - Age +/- 1 year
    - UTR +/- 0.5
    """
    if not player_data.get('utr_singles') or not player_data.get('age'):
        return []
        
    conn = get_db_connection()
    c = conn.cursor()
    
    gender = player_data.get('gender')
    age = player_data['age']
    utr = player_data['utr_singles']
    pid = player_data['player_id']
    
    # Range
    min_age = age - 1
    max_age = age + 1
    min_utr = utr - 0.5
    max_utr = utr + 0.5
    
    query = """
        SELECT player_id, name, utr_singles, country, age, gender 
        FROM players 
        WHERE gender = ? 
          AND age BETWEEN ? AND ?
          AND utr_singles BETWEEN ? AND ?
          AND player_id != ?
        ORDER BY ABS(utr_singles - ?) ASC
        LIMIT 5
    """
    
    c.execute(query, (gender, min_age, max_age, min_utr, max_utr, str(pid), utr))
    peers = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return peers

def calculate_clutch_score(player_data):
    """
    Calculate a 0-100 Clutch Score based on tiebreaks and 3-setters.
    Formula: 
      (TB_Win% * 50) + (3Set_Win% * 50)
    """
    tb_wins = player_data.get('tiebreak_wins') or 0
    tb_losses = player_data.get('tiebreak_losses') or 0
    ts_wins = player_data.get('three_set_wins') or 0
    ts_losses = player_data.get('three_set_losses') or 0
    
    tb_total = tb_wins + tb_losses
    ts_total = ts_wins + ts_losses
    
    if tb_total == 0 and ts_total == 0:
        return None # Not enough data
        
    tb_pct = (tb_wins / tb_total) if tb_total > 0 else 0.5 # Default to neutral if no TB
    ts_pct = (ts_wins / ts_total) if ts_total > 0 else 0.5
    
    # Weighting: If they have data in one but not other, weight heavily on the one present
    if tb_total == 0: clutch = ts_pct * 100
    elif ts_total == 0: clutch = tb_pct * 100
    else: clutch = (tb_pct * 50) + (ts_pct * 50)
    
    return round(clutch, 1)

def calculate_form_rating(matches, player_id):
    """
    Calculate Form Rating (0-100) based on last 5 matches.
    """
    if not matches:
        return None
        
    # Sort by date desc just in case
    # Assuming matches are dicts or Rows
    sorted_matches = sorted(matches, key=lambda x: x['date'], reverse=True)[:5]
    
    score = 50.0 # Base
    
    for m in sorted_matches:
        is_win = str(m['winner_id']) == str(player_id)
        
        # Determine opponent UTR (approx)
        # If we don't have opp UTR in match record, we assume parity or slight penalty
        # Match record usually has `winner_utr`, `loser_utr` or similar? 
        # let's check match schema or passed data.
        # usually `loser_name`, `winner_name`. UTRs might not be in older match imports.
        # But `import_matches.py` saves `winner_utr`, `loser_utr`? Let's check DB schema.
        # If not, we skip complexity for now.
        
        if is_win:
            score += 5
        else:
            score -= 5
            
    # Cap 0-100
    return max(0, min(100, score))

def calculate_advanced_metrics(matches, player_id):
    """
    Calculate:
    - Upset Factor (Wins vs Higher Rated)
    - Bounce Back (Win rate after loss)
    - Consistency (Matches per month)
    """
    if not matches:
        return {}

    # Sort ASC for chronological processing
    sorted_matches = sorted(matches, key=lambda x: x['date'])
    
    # Consistency
    if len(sorted_matches) > 1:
        start_date = datetime.strptime(sorted_matches[0]['date'].split('T')[0], '%Y-%m-%d')
        end_date = datetime.strptime(sorted_matches[-1]['date'].split('T')[0], '%Y-%m-%d')
        months = (end_date - start_date).days / 30.0
        matches_per_month = len(sorted_matches) / max(months, 1.0)
    else:
        matches_per_month = 0

    # Bounce Back
    losses = 0
    wins_after_loss = 0
    previous_was_loss = False
    
    for m in sorted_matches:
        is_winner = str(m['winner_id']) == str(player_id)
        
        if previous_was_loss:
            if is_winner:
                wins_after_loss += 1
            # Reset flag after the "next match" is played
            # (If they lost again, it counts as a failed bounce back, but sets up next one)
        
        if not is_winner:
            losses += 1
            previous_was_loss = True
        else:
            previous_was_loss = False
            
    bounce_back_rate = (wins_after_loss / losses * 100) if losses > 0 else None

    # Upset Factor
    # We need opponent UTR.
    # If match has winner_utr/loser_utr, use it.
    # Otherwise, rely on current Player UTR vs Opponent (imperfect).
    upset_wins = 0
    opportunities = 0
    
    for m in sorted_matches:
        is_winner = str(m['winner_id']) == str(player_id)
        
        # Try to get UTRs from match record (if they exist)
        # Using .get() just in case keys are missing
        w_utr = m.get('winner_utr')
        l_utr = m.get('loser_utr')
        
        if w_utr and l_utr:
            my_utr_val = w_utr if is_winner else l_utr
            opp_utr_val = l_utr if is_winner else w_utr
            
            # Define "Higher Rated" as +0.5 Diff
            if opp_utr_val > (my_utr_val + 0.5):
                opportunities += 1
                if is_winner:
                    upset_wins += 1
                    
    upset_rate = (upset_wins / opportunities * 100) if opportunities > 0 else None
    
    return {
        'matches_per_month': round(matches_per_month, 1),
        'bounce_back_rate': round(bounce_back_rate, 1) if bounce_back_rate is not None else None,
        'upset_rate': round(upset_rate, 1) if upset_rate is not None else None,
        'upset_wins': upset_wins,
        'upset_opportunities': opportunities
    }

def get_player_analysis(player_id):
    """
    Main entry point. Fetches data and computes metrics.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get Player
    c.execute("SELECT * FROM players WHERE player_id = ?", (str(player_id),))
    player = c.fetchone()
    
    if not player:
        conn.close()
        return None
        
    # Get Matches
    # Reuse valid SQL from tennis_db or just query here
    c.execute("""
        SELECT * FROM matches 
        WHERE winner_id = ? OR loser_id = ? 
        ORDER BY date DESC
    """, (str(player_id), str(player_id)))
    matches = [dict(row) for row in c.fetchall()]
    
    conn.close()
    
    # Calculate
    clutch = calculate_clutch_score(dict(player))
    form = calculate_form_rating(matches, player_id)
    # Cast to dict because row object is immutable/weird sometimes
    age_stats = analyze_age_cohort(dict(player)) 
    similar = find_similar_players(dict(player))
    advanced = calculate_advanced_metrics(matches, player_id)
    
    # New Advanced Stats
    try:
        highest_win = advanced_stats.get_highest_ranked_win(player_id)
        opening_wins = advanced_stats.get_consecutive_opening_wins(player_id)
        milestones = advanced_stats.get_career_milestones(player_id)
    except Exception as e:
        print(f"Error fetching advanced stats: {e}")
        highest_win = None
        opening_wins = {}
        milestones = {}
    
    return {
        'player_id': player_id,
        'clutch_score': clutch,
        'form_rating': form,
        'age_analysis': age_stats,
        'similar_players': similar,
        'advanced_metrics': advanced,
        'career_highlights': {
            'highest_ranked_win': highest_win,
            'consecutive_opening_wins': opening_wins,
            'career_milestones': milestones
        }
    }

def generate_mock_game_plan(player_id):
    """
    Simulate an AI response for the Game Plan.
    """
    stats = get_player_analysis(player_id)
    if not stats:
        return None
        
    name = "The Player" # Can fetch name if needed but stats has ID
    adv = stats.get('advanced_metrics', {})
    clutch = stats.get('clutch_score', 0)
    
    # Mock Logic
    mental_profile = "Balanced"
    if clutch < 45: mental_profile = "Prone to Pressure"
    elif clutch > 70: mental_profile = "Clutch Performer"
    
    tactics = []
    if adv.get('upset_rate', 0) < 25:
        tactics.append("- **Dont Overplay**: They struggle against higher-rated opponents. Just play your game.")
    if adv.get('bounce_back_rate', 0) > 60:
        tactics.append("- **Stay Alert**: They bounce back strong after losses. Don't let up if you win a set.")
        
    if not tactics:
        tactics.append("- **Run Them**: Their consistency is average.")

    return {
        "plan_text": f"""
### AI Opponent Intel
**Mental Profile**: {mental_profile}

**Recommended Game Plan**:
{''.join([f'{t} ' for t in tactics])}

**Prediction**:
Based on their recent form ({stats['form_rating']}), expect a competitive match but their Upset Rate suggests they struggle to punch up.
        """
    }
