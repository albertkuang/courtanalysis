import sqlite3
from datetime import datetime

def get_db_connection():
    conn = sqlite3.connect('tennis_data.db')
    conn.row_factory = sqlite3.Row
    return conn


def resolve_player_id(player_id):
    """
    Resolve a given player ID (Sackmann or UTR) to the UTR ID used in matches table.
    """
    if not player_id:
        return None
        
    # If it looks like a UTR ID (numeric), return it.
    # UTR IDs are usually strings of digits.
    if player_id.isdigit():
        return player_id
        
    # If it's a Sackmann ID (atp_..., wta_..., sackmann_...), resolve it.
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 1. Get Name from Sackmann Profiles
        s_id = player_id
        if s_id.startswith('sackmann-atp-'): s_id = s_id.replace('sackmann-atp-', 'atp_')
        elif s_id.startswith('sackmann-wta-'): s_id = s_id.replace('sackmann-wta-', 'wta_')
        elif s_id.startswith('sackmann_'): 
             raw = s_id.replace('sackmann_', '')
             # Try determining prefix? Assume lookup covers both or try variations
             # Sackmann IDs in profiles are usually atp_ or wta_ prefixed.
             pass
             
        # Try direct lookup in sackmann_profiles
        # We need to handle potential prefix mismatches if player_id is just 'sackmann_123'
        # But let's assume standard formats first.
        
        full_name = None
        c.execute("SELECT full_name FROM sackmann_profiles WHERE sackmann_id = ?", (s_id,))
        row = c.fetchone()
        if row:
            full_name = row[0]
        else:
            # Try variations
            if player_id.startswith('sackmann_'):
                # could be atp_... or wta_...
                suffix = player_id.replace('sackmann_', '')
                c.execute("SELECT full_name FROM sackmann_profiles WHERE sackmann_id = ? OR sackmann_id = ?", (f"atp_{suffix}", f"wta_{suffix}"))
                row = c.fetchone()
                if row:
                    full_name = row[0]

        if not full_name:
            conn.close()
            return player_id # Fallback to original, maybe it works?
            
        # 2. Get UTR ID from Players table by Name
        # Try exact match first
        c.execute("SELECT player_id FROM players WHERE name = ? COLLATE NOCASE", (full_name,))
        row = c.fetchone()
        if row:
            conn.close()
            return row[0]
            
        # Try partial match or regex?
        # "Iga Swiatek" vs "Swiatek I." - UTR names are usually full names "First Last".
        # Sackmann profiles are also "First Last".
        # So exact match should work often.
        
        conn.close()
        return player_id # Fallback
        
    except Exception as e:
        print(f"Error resolving player_id {player_id}: {e}")
        conn.close()
        return player_id

def get_highest_ranked_win(player_id_input):
    """
    Find the highest ranked opponent a player has defeated.
    Returns dict with match details and opponent rank.
    """
    player_id = resolve_player_id(player_id_input)
    conn = get_db_connection()
    c = conn.cursor()

    
    try:
        # Get all wins with winner/loser names
        c.execute("""
            SELECT m.match_id, m.date, m.tournament, m.score, m.round, m.winner_id, m.loser_id,
                   l.name as loser_name, l.player_id as loser_raw_id
            FROM matches m
            JOIN players l ON m.loser_id = l.player_id
            WHERE m.winner_id = ?
            ORDER BY m.date DESC
        """, (player_id,))
        wins = [dict(row) for row in c.fetchall()]
        
        if not wins:
            conn.close()
            return None
            
        # Collect all unique opponent IDs and Names to resolve to Sackmann IDs
        opponent_map = {} # raw_id -> {name, sackmann_ids: []}
        for w in wins:
            oid = w['loser_raw_id']
            name = w['loser_name']
            if oid not in opponent_map:
                opponent_map[oid] = {'name': name, 'sackmann_ids': []}
                
                # Check for direct ID candidates first
                if not oid.startswith('atp_') and not oid.startswith('wta_'):
                    opponent_map[oid]['sackmann_ids'].append(f"atp_{oid}")
                    opponent_map[oid]['sackmann_ids'].append(f"wta_{oid}")
                if oid.startswith('sackmann_'):
                     opponent_map[oid]['sackmann_ids'].append(f"atp_{oid.replace('sackmann_', '')}")
                     opponent_map[oid]['sackmann_ids'].append(f"wta_{oid.replace('sackmann_', '')}")

        # Resolve IDs via Name lookup in sackmann_profiles
        # This is CRITICAL because matches use UTR IDs, rankings use Sackmann IDs.
        # We must bridge matches.loser_id -> players.name -> sackmann_profiles.full_name -> sackmann_profiles.id
        
        for oid, data in opponent_map.items():
            name = data['name']
            if not name: continue
            
            # Simple Exact Match
            c.execute("SELECT sackmann_id FROM sackmann_profiles WHERE full_name = ? COLLATE NOCASE", (name,))
            rows = c.fetchall()
            if rows:
                for r in rows:
                    data['sackmann_ids'].append(r[0])
            else:
                # Try "Last First" <-> "First Last" swap if comma exists?
                # or just split
                parts = name.split()
                if len(parts) >= 2:
                    # Try matching lastname
                    # This is risky without strict checking, but let's try strict first.
                    pass

        # Collect all valid Sackmann IDs to fetch rankings for
        all_sackmann_ids = set()
        for data in opponent_map.values():
            for sid in data['sackmann_ids']:
                all_sackmann_ids.add(sid)
        
        if not all_sackmann_ids:
            conn.close()
            return None

        # Determine date range
        dates = [w['date'] for w in wins if w['date']]
        if not dates:
            conn.close()
            return None
        min_date = min(dates)
        
        # Batch fetch rankings
        placeholders = ','.join(['?'] * len(all_sackmann_ids))
        c.execute(f"""
            SELECT player_id, date, rank
            FROM rankings
            WHERE player_id IN ({placeholders})
            ORDER BY date DESC
        """, list(all_sackmann_ids))
        
        rankings_map = {} # sackmann_id -> list of (date, rank)
        for r in c.fetchall():
            pid = r['player_id']
            if pid not in rankings_map:
                rankings_map[pid] = []
            rankings_map[pid].append({'date': r['date'], 'rank': r['rank']})
            
        best_win = None
        min_rank = 99999
        
        for match in wins:
            loser_id = match['loser_raw_id']
            match_date = match['date']
            if not match_date: continue
            
            # Get candidates from our map
            cands = opponent_map.get(loser_id, {}).get('sackmann_ids', [])
                 
            # Find applicable ranking
            found_rank = None
            found_date = None
            
            for cid in cands:
                if cid in rankings_map:
                    # Find latest ranking on or before match_date
                    for r in rankings_map[cid]:
                        if r['date'] <= match_date:
                             match_dt = datetime.strptime(match_date[:10], '%Y-%m-%d')
                             rank_dt = datetime.strptime(r['date'][:10], '%Y-%m-%d')
                             # Allow ranking to be up to 40 days old (approx 1 month + margin)
                             if (match_dt - rank_dt).days < 60:
                                 found_rank = r['rank']
                                 found_date = r['date']
                                 break 
                    if found_rank:
                        break
            
            if found_rank is not None and found_rank < min_rank:
                min_rank = found_rank
                best_win = match
                best_win['loser_rank'] = found_rank
                best_win['rank_date'] = found_date
        
        conn.close()
        return best_win
        
    except Exception as e:
        print(f"Error in get_highest_ranked_win: {e}")
        conn.close()
        return None


def get_consecutive_opening_wins(player_id_input, tourney_levels=['M', 'PM', '1000']):
    """
    Calculate consecutive wins in opening matches at specified tournament levels.
    """
    player_id = resolve_player_id(player_id_input)
    conn = get_db_connection()
    c = conn.cursor()
    
    placeholders = ','.join(['?'] * len(tourney_levels))
    query = f"""
        SELECT m.match_id, m.date, m.tournament, m.round, m.winner_id, m.loser_id
        FROM matches m
        WHERE (m.winner_id = ? OR m.loser_id = ?)
          AND m.tourney_level IN ({placeholders})
        ORDER BY m.date ASC
    """
    
    try:
        c.execute(query, (player_id, player_id, *tourney_levels))
        matches = [dict(row) for row in c.fetchall()]
        
        # Group by Tournament
        # We need to identify unique tournaments. (Name + Year) or (Date cluster)
        # Using (Tournament Name + Year) is safest if we extract year.
        
        tournaments = {}
        for m in matches:
            date_str = m['date'][:10] if m['date'] else 'xxxx'
            year = date_str[:4]
            t_key = f"{m['tournament']}_{year}"
            
            if t_key not in tournaments:
                tournaments[t_key] = []
            tournaments[t_key].append(m)
            
        # Analyze opening matches
        streak = 0
        max_streak = 0
        current_streak = 0
        
        # Sort tournaments by date
        sorted_keys = sorted(tournaments.keys(), key=lambda k: tournaments[k][0]['date'])
        
        history = []
        
        for t_key in sorted_keys:
            t_matches = tournaments[t_key]
            # Find first match (opening match)
            # Sort by date asc
            t_matches.sort(key=lambda x: x['date'])
            opening_match = t_matches[0]
            
            is_winner = str(opening_match['winner_id']) == str(player_id)
            
            result = {
                'tournament': t_key,
                'date': opening_match['date'],
                'won_opener': is_winner,
                'opponent': opening_match['loser_id'] if is_winner else opening_match['winner_id']
            }
            history.append(result)
            
            if is_winner:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
                
        conn.close()
        return {
            "current_streak": current_streak,
            "max_streak": max_streak,
            "history_count": len(history),
            "history": history
        }
        
    except Exception as e:
        print(f"Error in get_consecutive_opening_wins: {e}")
        conn.close()
        return {"error": str(e)}

def get_career_milestones(player_id_input):
    """
    Analyze career rounds to find milestones (e.g. 1st QF, 2nd SF, etc.)
    """
    player_id = resolve_player_id(player_id_input)
    conn = get_db_connection()
    c = conn.cursor()
    
    # We look for high level rounds: QF, SF, F, W
    target_rounds = ['QF', 'SF', 'F'] # 'W' is implicitly winning F
    
    query = """
        SELECT m.match_id, m.date, m.tournament, m.round, m.tourney_level, m.winner_id, m.loser_id
        FROM matches m
        WHERE (m.winner_id = ? OR m.loser_id = ?)
          AND m.round IN ('QF', 'SF', 'F')
        ORDER BY m.date ASC
    """
    
    try:
        c.execute(query, (player_id, player_id))
        matches = [dict(row) for row in c.fetchall()]
        
        milestones = {
            'QF': [],
            'SF': [],
            'F':  [],
            'Titles': []
        }
        
        for m in matches:
            rd = m['round']
            is_winner = str(m['winner_id']) == str(player_id)
            
            # If they reached this round, they played in it.
            # We record the appearance.
            milestone_entry = {
                'date': m['date'],
                'tournament': m['tournament'],
                'level': m['tourney_level'],
                'result': 'Won' if is_winner else 'Lost'
            }
            
            if rd in milestones:
                milestones[rd].append(milestone_entry)
            
            # Special case for Titles (Winning a Final)
            if rd == 'F' and is_winner:
                milestones['Titles'].append(milestone_entry)
                
        conn.close()
        return milestones
        
    except Exception as e:
        print(f"Error in get_career_milestones: {e}")
        conn.close()
        return {}

def get_age_records(tourney_level='G', min_age=35):
    """
    Find players who won matches at a certain age in certain levels.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    # We need player birth_date
    # Calculate age at match date
    
    # Optimization: Filter for players born before (Now - Min Age)
    # We can approximate 'now' as late 2025/2026.
    # To be safe and capture historical matches:
    # We want (MatchDate - BirthDate) >= MinAge years
    # So BirthDate <= MatchDate - MinAge years
    # Since MatchDate varies, we can at least filter players born before reasonable threshold.
    # E.g. born before 1990 for 35+ in 2025.
    
    query = f"""
        SELECT m.date, m.tournament, m.score, m.round,
               w.name, w.birth_date, w.player_id
        FROM matches m
        JOIN players w ON m.winner_id = w.player_id
        WHERE m.tourney_level = ?
          AND w.birth_date IS NOT NULL
          AND w.birth_date < date('now', '-{min_age} years')
        ORDER BY m.date DESC
        LIMIT 1000
    """
    
    try:
        c.execute(query, (tourney_level,))
        matches = [dict(row) for row in c.fetchall()]
        
        records = []
        for m in matches:
            try:
                match_date = datetime.strptime(m['date'][:10], '%Y-%m-%d')
                birth_date = datetime.strptime(m['birth_date'][:10], '%Y-%m-%d')
                
                age_days = (match_date - birth_date).days
                age_years = age_days / 365.25
                
                if age_years >= min_age:
                    m['age'] = round(age_years, 2)
                    m['age_str'] = f"{int(age_years)}y {int((age_years % 1) * 365)}d"
                    records.append(m)
            except:
                continue
                
        # Deduplicate by player (keep oldest win? or all?)
        # Let's keep top 50 oldest wins
        records.sort(key=lambda x: x['age'], reverse=True)
        
        conn.close()
        return records[:50]
        
    except Exception as e:
        print(f"Error in get_age_records: {e}")
        conn.close()
        return []
