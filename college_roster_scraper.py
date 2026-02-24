"""
U.S. College Tennis Roster Scraper
Searches for colleges by division (D1/D2/D3) and fetches team rosters with UTR metrics.
"""

import requests
import csv
import sys
import argparse
import time
from datetime import datetime
import concurrent.futures
import tennis_db

# ============================================
# CONFIGURATION
# ============================================
from config import UTR_CONFIG
CONFIG = UTR_CONFIG

LOGIN_URL = "https://app.utrsports.net/api/v1/auth/login"
COLLEGE_SEARCH_URL = "https://app.utrsports.net/api/v2/search/colleges"
# Roster endpoint pattern: GET /api/v1/club/{club_id}/members
ROSTER_URL_TEMPLATE = "https://app.utrsports.net/api/v1/club/{}/members"

# Term mappings for divisions if needed for search queries
DIVISION_TERMS = {
    'D1': 'NCAA Division I',
    'D2': 'NCAA Division II',
    'D3': 'NCAA Division III',
    'NAIA': 'NAIA',
    'JUCO': 'Junior College'
}

# ============================================
# LOGIN
# ============================================
def login():
    print("Logging in to UTR...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Content-Type": "application/json"
    }
    
    response = requests.post(LOGIN_URL, json={
        "email": CONFIG['email'],
        "password": CONFIG['password']
    }, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"Login failed: {response.status_code}")
    
    data = response.json()
    token = data.get('jwt') or data.get('token')
    
    if not token:
        for cookie in response.cookies:
            if cookie.name == 'jwt':
                token = cookie.value
                break
    
    print("Login successful!")
    return {'token': token, 'cookies': response.cookies}

# ============================================
# SEARCH / FIND COLLEGE
# ============================================
def find_college_by_name(auth_info, name, preferred_gender='M'):
    """
    Search for a specific college by name and return its details, 
    prioritizing the club ID for the preferred gender.
    """
    headers = {}
    if auth_info.get('token'):
        headers['Authorization'] = f"Bearer {auth_info['token']}"
    
    params = {
        'query': name,
        'top': 5
    }
    
    try:
        response = requests.get(COLLEGE_SEARCH_URL, params=params, headers=headers, cookies=auth_info.get('cookies'))
        if response.status_code != 200:
            return None
            
        data = response.json()
        hits = data.get('hits', [])
        
        # Exact match or best fuzzy match
        target_hit = None
        for hit in hits:
            source = hit.get('source', hit)
            h_name = source.get('name', '').lower()
            if name.lower() == h_name:
                target_hit = source
                break
            if name.lower() in h_name or h_name in name.lower():
                if not target_hit:
                    target_hit = source
        
        if target_hit:
            # Extract gender-specific club ID
            m_id = target_hit.get('mensClubId')
            w_id = target_hit.get('womensClubId')
            
            # Select appropriate club ID
            club_id = target_hit.get('clubId') or target_hit.get('id') # Default
            if preferred_gender == 'M' and m_id:
                club_id = m_id
            elif preferred_gender == 'F' and w_id:
                club_id = w_id
                
            return {
                'name': target_hit.get('name'),
                'id': target_hit.get('id'),
                'clubId': club_id
            }
    except Exception as e:
        print(f"Error finding college {name}: {e}")
        
    return None

def search_colleges(auth_info, division, limit=50):
    """
    Search for colleges. 
    Note: UTR College search API behavior needs to be handled carefully.
    We'll try to filter by division if the API supports it, or search broadly.
    """
    headers = {}
    if auth_info.get('token'):
        headers['Authorization'] = f"Bearer {auth_info['token']}"
    
    colleges = []
    skip = 0
    batch_size = 50
    
    print(f"Searching for {division} colleges...")
    
    # The API might expect 'query' or specific filters. 
    # Based on standard UTR patterns, we'll try a broad search and filter client-side if needed,
    # or use the division term as the query.
    
    # API search is fuzzy. We will use a broad search (empty string) to get maximum results
    # and then strictly filter client-side by division.
    # But if the user wants ALL, we just take everything.
    search_term = "" 
    
    # Mapping our args to API division shortNames
    # API tends to use: D1, D2, D3, NAIA, JUCO
    target_div = division
    
    while len(colleges) < limit:
        params = {
            'query': search_term,
            'top': batch_size,
            'skip': skip
        }
        
        try:
            response = requests.get(COLLEGE_SEARCH_URL, params=params, headers=headers, cookies=auth_info.get('cookies'))
            if response.status_code != 200:
                print(f"Search failed: {response.status_code}")
                break
                
            data = response.json()
            hits = data.get('hits', [])
            
            if not hits:
                break
                
            for hit in hits:
                source = hit.get('source', hit)
                
                # Div Check
                conf = source.get('conference', {})
                div_obj = conf.get('division', {}) if conf else {}
                short_name = div_obj.get('shortName') # e.g. D1, D2
                
                if division != 'ALL':
                    if short_name != target_div:
                        continue
                
                col_name = source.get('name', '')
                col_id = source.get('id')
                # For roster, we prefer gender-specific club IDs if available
                # source often has mensClubId / womensClubId
                # But here we just get the base ID and find_college/get_roster handles club resolution usually?
                # Actually get_roster takes a club_id. 
                # Let's try to grab the gender-specific one here if we can.
                
                # Correction: The search result 'source' has mensClubId and womensClubId directly.
                club_id = source.get('clubId') or source.get('id')
                
                colleges.append({
                    'name': col_name,
                    'id': col_id,
                    'clubId': club_id, # get_roster might need to refine this based on gender
                    'mensClubId': source.get('mensClubId'),
                    'womensClubId': source.get('womensClubId'),
                    'division': short_name or division
                })
                
                if len(colleges) >= limit:
                    break
            
            skip += batch_size
            
        except Exception as e:
            print(f"Error searching colleges: {e}")
            break
            
    print(f"Found {len(colleges)} colleges.")
    return colleges

# ============================================
# GET ROSTER
# ============================================
def get_college_roster(auth_info, club_id, gender):
    """
    Fetch roster for a specific college (club_id) using Player Search API.
    Filter by gender ('M' or 'F') and exclude inactive/non-varsity players.
    """
    headers = {}
    if auth_info.get('token'):
        headers['Authorization'] = f"Bearer {auth_info['token']}"
        
    roster = []
    skip = 0
    batch_size = 100
    current_year = 2025 # 2024-25 season seniors graduate 2025
    
    while True:
        params = {
            'top': batch_size,
            'skip': skip,
            'gender': 'M' if gender == 'M' else 'F',
            'utrType': 'verified',
            'clubId': club_id
        }
        
        try:
            response = requests.get("https://app.utrsports.net/api/v2/search/players", params=params, headers=headers, cookies=auth_info.get('cookies'))
            if response.status_code != 200:
                break
                
            data = response.json()
            hits = data.get('hits', [])
            
            if not hits:
                break
            
            for hit in hits:
                m = hit.get('source', hit)
                
                # 1. Filtering for active collegiate roster
                # Active players MUST have playerCollegeDetails or a gradYear in the future
                col_details = m.get('playerCollegeDetails')
                is_active = False
                
                if col_details:
                    # If they have details, they are almost certainly active/committed
                    # We check gradYear if available to filter out extremely old ones (though usually they are removed)
                    gy_str = col_details.get('gradYear')
                    if gy_str:
                        try:
                            gy = int(gy_str.split('-')[0])
                            if gy >= current_year:
                                is_active = True
                        except:
                            is_active = True
                    else:
                        is_active = True
                
                # Additional heuristic: If no details but gradYear is reasonably future
                # But be careful, many high schoolers have gradYear 2026/27 but aren't in college yet.
                # However, if they are in a college CLUB roster, and have gradYear 2025/26/27/28, they are likely the players.
                grad_year = m.get('gradYear')
                if not is_active and grad_year:
                    try:
                        gy = int(grad_year)
                        if current_year <= gy <= current_year + 4:
                            is_active = True
                    except: pass

                if not is_active:
                    continue

                # 3. UTR Check - Real roster players have ratings
                utr = m.get('singlesUtr', 0) or 0
                d_utr = m.get('doublesUtr', 0) or 0
                
                if utr == 0 and d_utr == 0:
                    continue

                # Basic player info
                roster.append({
                    'id': m.get('id'),
                    'name': m.get('displayName') or f"{m.get('firstName')} {m.get('lastName')}",
                    'gradYear': grad_year,
                    'utr': utr,
                    'doublesUtr': d_utr,
                    'gender': gender
                })
            
            if len(hits) < batch_size:
                break
                
            skip += batch_size
            time.sleep(0.2) # Polite delay
            
        except Exception as e:
            print(f"Error fetching page for {club_id}: {e}")
            break
            
    return roster



# ============================================
# EXTRACT & FETCH DETAILED METRICS
# (Adapted from scraper_analyst.py)
# ============================================
def fetch_player_metrics(auth_info, player_basic):
    """
    Fetch full metrics for a player and save matches/history to DB.
    """
    player = {
        'id': str(player_basic['id']),
        'name': player_basic['name'],
        'school': player_basic.get('school_name'),
        'division': player_basic.get('division'),
        'utr': player_basic.get('utr', 0),
        'doublesUtr': player_basic.get('doublesUtr', ''),
        'gender': player_basic.get('gender', 'M'), # Default M if missing
        # Defaults
        'peakUtr': '-', 'minRating': '-', 'trend': '-', 'yearDelta': None,
        'winLoss': '-', 'winPercent': '-', 'upsetRatio': '-', 'avgOppUtr': '-',
        'threeSetRecord': '-', 'recentForm': '-', 'tournamentCount': 0,
        'higherRatedWinPct': '-', 'tiebreakRecord': '-', 'comebackWins': 0,
        'age': '-', 'location': '-', 'country': '-', 'proRank': '-',
        'profileUrl': f"https://app.utrsports.net/profiles/{player_basic['id']}"
    }

    headers = {}
    if auth_info.get('token'):
        headers['Authorization'] = f"Bearer {auth_info['token']}"
    
    import datetime as dt
    one_year_ago = dt.datetime.now() - dt.timedelta(days=365)
    
    # DB Connection for this thread
    conn = tennis_db.get_connection()
    
    try:
        # 1. Fetch Profile Info (Age, Country, Location)
        profile_url = f"https://app.utrsports.net/api/v1/player/{player['id']}"
        try:
            p_res = requests.get(profile_url, headers=headers, cookies=auth_info.get('cookies'))
            if p_res.status_code == 200:
                p_data = p_res.json()
                player['location'] = p_data.get('location', {}).get('display', '-')
                player['country'] = p_data.get('nationality', '-')
                
                # Age
                age = p_data.get('age')
                if age:
                    player['age'] = age
                
                # 3-Month Trend
                player['trend'] = p_data.get('threeMonthRatingChangeDetails', {}).get('ratingDifference')
                
                # Pro Rank
                rankings = p_data.get('thirdPartyRankings', [])
                if rankings:
                    rank_obj = next((r for r in rankings if r.get('source') in ['ATP', 'WTA']), None)
                    if rank_obj:
                        player['proRank'] = f"{rank_obj.get('source')} #{rank_obj.get('rank')}"
        except: pass

        # 2. Fetch Results (Metrics & DB Save)
        results_url = f"https://app.utrsports.net/api/v1/player/{player['id']}/results"
        
        all_wins = 0
        all_losses = 0
        upsets = 0
        opponent_utrs = []
        three_set_wins = 0
        three_set_losses = 0
        all_matches = []
        event_ids = set()
        higher_rated_wins = 0
        higher_rated_matches = 0
        tiebreak_wins = 0
        tiebreak_losses = 0
        comeback_wins = 0
        player_utrs_in_matches = []
        
        skip = 0
        batch_size = 100
        done = False
        
        while not done:
            r_params = {'top': batch_size, 'skip': skip}
            try:
                resp_res = requests.get(results_url, params=r_params, headers=headers, cookies=auth_info.get('cookies'))
            except: 
                break
                
            if resp_res.status_code != 200: break
            
            r_data = resp_res.json()
            events = r_data.get('events', [])
            if not events: break
            
            found_old = False
            for event in events:
                # Date check
                event_date_str = event.get('startDate') or event.get('endDate')
                event_in_range = True
                event_date = None
                
                if event_date_str:
                    try:
                        event_date = dt.datetime.fromisoformat(event_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                        if event_date < one_year_ago:
                            found_old = True
                            event_in_range = False
                    except: pass
                
                if not event_in_range: continue
                event_ids.add(event.get('id'))
                
                for draw in event.get('draws', []):
                    for result in draw.get('results', []):
                        # Result date check
                        result_date_str = result.get('date') or result.get('resultDate')
                        result_date = None
                        if result_date_str:
                            try:
                                result_date = dt.datetime.fromisoformat(result_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                                if result_date < one_year_ago: continue
                            except: pass
                            
                        players_data = result.get('players', {})
                        winner = players_data.get('winner1', {})
                        loser = players_data.get('loser1', {})
                        score = result.get('score', {})
                        
                        pid_str = str(player['id'])
                        is_winner = str(winner.get('id')) == pid_str
                        is_loser = str(loser.get('id')) == pid_str
                        
                        if not is_winner and not is_loser: continue
                        
                        # === DB SAVE MATCH ===
                        try:
                             # Save opponent
                             opp_obj = loser if is_winner else winner
                             if opp_obj and opp_obj.get('id'):
                                 opp_name = opp_obj.get('displayName') or f"{opp_obj.get('firstName', '')} {opp_obj.get('lastName', '')}".strip()
                                 if opp_name:
                                     tennis_db.save_player(conn, {
                                         'player_id': str(opp_obj.get('id')),
                                         'name': opp_name,
                                         'gender': player['gender'], # Assuming same gender
                                         'utr_singles': opp_obj.get('singlesUtr'),
                                         'utr_doubles': opp_obj.get('doublesUtr'),
                                         'age': None # We don't know opponent age
                                     })

                             # Save Match
                             match_id = result.get('id')
                             if match_id:
                                 score_str = ""
                                 for i in range(1, 6):
                                     s_set = score.get(str(i))
                                     if s_set:
                                         score_str += f"{s_set.get('winner')}-{s_set.get('loser')} "
                                     else: break
                                 
                                 m_date = result_date or event_date
                                 m_date_iso = m_date.isoformat() if m_date else None

                                 tennis_db.save_match(conn, {
                                     'match_id': match_id,
                                     'date': m_date_iso,
                                     'winner_id': str(winner.get('id')),
                                     'loser_id': str(loser.get('id')),
                                     'score': score_str.strip(),
                                     'tournament': event.get('name'),
                                     'round': draw.get('name'),
                                     'source': 'UTR',
                                     'winner_utr': winner.get('singlesUtr'),
                                     'loser_utr': loser.get('singlesUtr'),
                                     'processed_player_id': str(player['id'])
                                 })
                        except Exception as e_db:
                            # print(f"DB Error: {e_db}")
                            pass
                        # =====================
                        
                        num_sets = len(score) if score else 0
                        is_three_set = num_sets >= 3
                        
                        # Tiebreaks
                        for _, sdata in (score or {}).items():
                            if sdata and sdata.get('tiebreak') is not None:
                                w_tb = sdata.get('winnerTiebreak', 0) or 0
                                l_tb = sdata.get('tiebreak', 0) or 0
                                if (is_winner and w_tb > l_tb) or (is_loser and l_tb > w_tb):
                                    tiebreak_wins += 1
                                else:
                                    tiebreak_losses += 1

                        # Comeback
                        if is_winner and score and '1' in score:
                            fs = score['1']
                            if fs and fs.get('winner', 0) < fs.get('loser', 0):
                                comeback_wins += 1

                        if is_winner:
                            all_wins += 1
                            my_utr = winner.get('singlesUtr') or winner.get('utr') or 0
                            opp_utr = loser.get('singlesUtr') or loser.get('utr') or 0
                            
                            if opp_utr > 0: opponent_utrs.append(opp_utr)
                            if opp_utr > my_utr:
                                upsets += 1
                                higher_rated_wins += 1
                                higher_rated_matches += 1
                            
                            if is_three_set: three_set_wins += 1
                            if my_utr > 0: player_utrs_in_matches.append(my_utr)
                            all_matches.append((result_date_str or event_date_str, True))
                            
                        elif is_loser:
                            all_losses += 1
                            my_utr = loser.get('singlesUtr') or loser.get('utr') or 0
                            opp_utr = winner.get('singlesUtr') or winner.get('utr') or 0
                            
                            if opp_utr > 0: opponent_utrs.append(opp_utr)
                            if opp_utr > my_utr: higher_rated_matches += 1
                            
                            if is_three_set: three_set_losses += 1
                            if my_utr > 0: player_utrs_in_matches.append(my_utr)
                            all_matches.append((result_date_str or event_date_str, False))
            
            if found_old:
                if len(events) > 0:
                     last_event = events[-1]
                     last_ed = last_event.get('startDate') or last_event.get('endDate')
                     if last_ed:
                         try:
                            ld = dt.datetime.fromisoformat(last_ed.replace('Z', '+00:00')).replace(tzinfo=None)
                            if ld < one_year_ago:
                                pass # In generic logic we stop, but here we scan all events
                         except: pass
            
            skip += batch_size
            if skip >= 300: done = True
            
            # Commit batch
            try: conn.commit()
            except: pass
            
        # Calc Metrics
        player['winLoss'] = f"{all_wins}W-{all_losses}L"
        tot = all_wins + all_losses
        player['winPercent'] = f"{(all_wins/tot)*100:.1f}%" if tot > 0 else "0.0%"
        player['upsetRatio'] = f"{upsets}/{all_wins} ({upsets/all_wins:.0%})" if all_wins > 0 else "0/0"
        
        if opponent_utrs:
            player['avgOppUtr'] = f"{sum(opponent_utrs)/len(opponent_utrs):.2f}"
            
        ts_tot = three_set_wins + three_set_losses
        player['threeSetRecord'] = f"{three_set_wins}W-{three_set_losses}L"
        if ts_tot > 0: player['threeSetRecord'] += f" ({(three_set_wins/ts_tot)*100:.0f}%)"
        
        # Recent Form
        matches_sorted = sorted(all_matches, key=lambda x: x[0] or '', reverse=True)[:10]
        rw = sum(1 for m in matches_sorted if m[1])
        rl = len(matches_sorted) - rw
        player['recentForm'] = f"{rw}W-{rl}L"
        
        player['tournamentCount'] = len(event_ids)
        
        if higher_rated_matches > 0:
            player['higherRatedWinPct'] = f"{higher_rated_wins}/{higher_rated_matches} ({higher_rated_wins/higher_rated_matches:.0%})"
        
        tb_tot = tiebreak_wins + tiebreak_losses
        player['tiebreakRecord'] = f"{tiebreak_wins}W-{tiebreak_losses}L"
        
        player['comebackWins'] = comeback_wins
        
        if player_utrs_in_matches:
            player['peakUtr'] = max(player_utrs_in_matches)
            player['minRating'] = min(player_utrs_in_matches)
            
        # 3. History (Year Delta) & DB Save
        stats_url = f"https://app.utrsports.net/api/v1/player/{player['id']}/stats"
        try:
            s_res = requests.get(stats_url, params={'type': 'singles', 'resultType': 'verified', 'Months': 12}, headers=headers, cookies=auth_info.get('cookies'))
            if s_res.status_code == 200:
                s_data = s_res.json()
                
                # Update peak/min if stats are better
                if s_data.get('maxRating') and (player['peakUtr'] == '-' or s_data['maxRating'] > player.get('peakUtr', 0)):
                    player['peakUtr'] = s_data['maxRating']
                    
                history = s_data.get('extendedRatingProfile', {}).get('history') or s_data.get('ratingHistory', [])
                if history:
                    curr = player['utr']
                    prior = None
                    closest_dist = float('inf')
                    for h in history:
                        try:
                            d = dt.datetime.fromisoformat(h['date'].replace('Z','+00:00')).replace(tzinfo=None)
                            dist = abs((d - one_year_ago).total_seconds())
                            if dist < closest_dist:
                                closest_dist = dist
                                prior = h.get('rating')
                            
                            # Save History
                            tennis_db.save_history(conn, {
                                'player_id': str(player['id']),
                                'date': h.get('date'),
                                'rating': h.get('rating'),
                                'type': 'singles'
                            })
                        except: pass
                    
                    if prior:
                        player['yearDelta'] = round(curr - prior, 2)
        except: pass

        # === SAVE PLAYER PROFILE TO DB ===
        try:
             p_data = {
                 'player_id': str(player['id']),
                 'name': player.get('name'),
                 'college': player.get('school'),
                 'country': player.get('country'),
                 'gender': player.get('gender'),
                 'utr_singles': player.get('utr'),
                 'utr_doubles': player.get('doublesUtr'),
                 'age': player.get('age') if player.get('age') != '-' else None
             }
             tennis_db.save_player(conn, p_data)
        except: pass

    except Exception as e:
        # print(f"Err metric {player['id']}: {e}")
        pass
    finally:
        try:
            conn.commit()
            conn.close()
        except: pass
        
    return player

# ============================================
# MAIN
# ============================================
def main():
    parser = argparse.ArgumentParser(description='College Tennis Roster Scraper')
    parser.add_argument('--division', default='D1', help='D1, D2, D3, NAIA, JUCO, or ALL')
    parser.add_argument('--gender', default='M', help='M or F')
    parser.add_argument('--count', type=int, default=500, help='Max players')
    parser.add_argument('--test', action='store_true', help='Test mode (limited fetch)')
    parser.add_argument('--quick', action='store_true', help='Skip detailed metrics (faster)')
    
    parser.add_argument('--file', help='Path to file with college names (one per line)')
    
    args = parser.parse_args()
    
    print(f"Starting College Roster Scraper for {args.division} - {args.gender}")
    auth_info = login()
    tennis_db.init_db()
    
    all_players_basic = []
    
    if args.file:
        print(f"Reading college names from {args.file}...")
        with open(args.file, 'r', encoding='utf-8') as f:
            college_names = [line.strip() for line in f if line.strip()]
        
        print(f"Found {len(college_names)} college names in file.")
        if args.test:
            college_names = college_names[:5]
            
        for name in college_names:
            col = find_college_by_name(auth_info, name, preferred_gender=args.gender)
            if col:
                print(f"Searching roster for {col['name']} (Club ID: {col['clubId']})...")
                roster = get_college_roster(auth_info, col['clubId'], args.gender)
                for p in roster:
                    p['school_name'] = col['name']
                    p['division'] = args.division
                    all_players_basic.append(p)
                print(f"   found {len(roster)} players")
                time.sleep(0.5)
            else:
                print(f"College not found: {name}")
    else:
        # Legacy search-based approach
        search_divisions = [args.division] if args.division != 'ALL' else ['D1', 'D2', 'D3']
        for div in search_divisions:
            colleges = search_colleges(auth_info, div, limit=args.count if args.count > 50 else 500) # Ensure we find enough
            for i, col in enumerate(colleges):
                print(f"[{i+1}/{len(colleges)}] Fetching roster for {col['name']} ({div})...")
                
                # Determine best Club ID
                cid = col['clubId']
                if args.gender == 'M' and col.get('mensClubId'): cid = col['mensClubId']
                elif args.gender == 'F' and col.get('womensClubId'): cid = col['womensClubId']
                
                roster = get_college_roster(auth_info, cid, args.gender)
                for p in roster:
                    p['school_name'] = col['name']
                    p['division'] = div
                    all_players_basic.append(p)
                print(f"   found {len(roster)} players")
                time.sleep(0.5)
                if args.test and i >= 2: break
    
    # Sort by UTR desc
    all_players_basic.sort(key=lambda x: x['utr'], reverse=True)
    
    # Limit
    if args.count:
        all_players_basic = all_players_basic[:args.count]
    
    final_data = []
    
    if args.quick:
        print("\nSkipping detailed metrics (Quick Mode)...")
        # Populate defaults for missing fields
        for p in all_players_basic:
            # Create a simple dict matching output structure
            simple_p = {
                'id': p['id'],
                'name': p['name'],
                'school': p['school_name'],
                'division': p['division'],
                'utr': p['utr'],
                'doublesUtr': p['doublesUtr'],
                'peakUtr': '-', 'minRating': '-', 'trend': '-', 'yearDelta': None,
                'winLoss': '-', 'winPercent': '-', 'upsetRatio': '-', 'avgOppUtr': '-',
                'threeSetRecord': '-', 'recentForm': '-', 'tournamentCount': 0, 
                'higherRatedWinPct': '-', 'tiebreakRecord': '-', 'comebackWins': 0,
                'age': '-', 'location': '-', 'country': '-', 'proRank': '-',
                'profileUrl': f"https://app.utrsports.net/profiles/{p['id']}"
            }
            final_data.append(simple_p)
    else:    
        print(f"\nFetching detailed metrics for top {len(all_players_basic)} players...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_player_metrics, auth_info, p): p for p in all_players_basic}
            
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                try:
                    data = future.result()
                    final_data.append(data)
                    sys.stdout.write(f"\rProgress: {i+1}/{len(all_players_basic)}")
                    sys.stdout.flush()
                except Exception as e:
                    # print(f"Error: {e}")
                    pass
                
    # Sort again fully
    final_data.sort(key=lambda x: x.get('utr', 0), reverse=True)
    
    # OUTPUT CSV
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"College_{args.division}_{'Male' if args.gender=='M' else 'Female'}_{date_str}.csv"
    
    cols = [
        'Rank', 'Name', 'College', 'Division', 'Singles UTR', 'Doubles UTR', 
        'Peak UTR', 'Min Rating', '3-Month Trend', '1-Year Delta', 
        'Win Record', 'Win %', 'Upset Ratio', 'Avg Opp UTR', 
        '3-Set Record', 'Recent Form (L10)', 'Tournaments', 'vs Higher Rated',
        'Tiebreak Record', 'Comeback Wins', 'Age', 'Country', 'Location', 
        'Pro Rank', 'Profile URL'
    ]
    
    print(f"\n\nSaving to {filename}...")
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        for i, p in enumerate(final_data):
            writer.writerow([
                i+1, p['name'], p['school'], p['division'], p['utr'], p['doublesUtr'],
                p['peakUtr'], p['minRating'], p['trend'], p['yearDelta'],
                p['winLoss'], p['winPercent'], p['upsetRatio'], p['avgOppUtr'],
                p['threeSetRecord'], p['recentForm'], p['tournamentCount'], p['higherRatedWinPct'],
                p['tiebreakRecord'], p['comebackWins'], p['age'], p['country'], p['location'],
                p['proRank'], p['profileUrl']
            ])
            
    print("Done.")

if __name__ == "__main__":
    main()
