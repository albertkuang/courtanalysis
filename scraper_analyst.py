"""
UTR Player Scraper - Multi-Country Merge Version (Python)
Searches multiple countries and merges results to get TRUE global top juniors
"""

import requests
import csv
import sys
import argparse
from datetime import datetime
import time
import tennis_db

# ============================================
# ARGUMENT PARSING
# ============================================
parser = argparse.ArgumentParser(description='UTR Player Scraper')
parser.add_argument('--country', default='USA', help='ISO-3 Country Code (e.g. CAN) or ALL')
parser.add_argument('--gender', default='M', help='M or F')
parser.add_argument('--category', default='junior', help='junior, adult, or all')
parser.add_argument('--count', type=int, default=100, help='Number of players to fetch')
parser.add_argument('--history', action='store_true', help='Fetch 1-year UTR delta')
parser.add_argument('--player', help='Search for a specific player name')

args = parser.parse_args()

PARAMS = {
    'COUNTRY': args.country,
    'GENDER': args.gender,
    'CATEGORY': args.category,
    'TOP_COUNT': args.count,
    'HISTORY': args.history,
    'PLAYER': args.player
}

# Major tennis countries to search when using --country=MAJOR
MAJOR_TENNIS_COUNTRIES = [
    'USA', 'CAN', 'GBR', 'AUS', 'FRA', 'DEU', 'ESP', 'ITA', 'JPN', 'CHN',
    'RUS', 'CZE', 'SRB', 'POL', 'NLD', 'BEL', 'SWE', 'AUT', 'SVK', 'UKR',
    'BRA', 'ARG', 'MEX', 'KOR', 'IND', 'NZL', 'ZAF', 'ISR', 'TUR', 'GRC',
    'ROU', 'HUN', 'PRT', 'CHE', 'BGR', 'HRV', 'SVN', 'LUX', 'THA', 'TWN'
]

from config import UTR_CONFIG

CONFIG = UTR_CONFIG

LOGIN_URL = "https://app.utrsports.net/api/v1/auth/login"
SEARCH_URL = "https://app.utrsports.net/api/v2/search/players"

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
# SEARCH PLAYERS
# ============================================
def search_players(auth_info, filters):
    params = {
        'top': filters.get('top', 100),
        'skip': filters.get('skip', 0),
        'gender': filters.get('gender'),
        'utrMin': filters.get('min_utr', 1),
        'utrMax': filters.get('max_utr', 16.5),
        'utrType': 'verified'
    }
    
    if filters.get('max_utr'):
        params['utrMax'] = filters['max_utr']
    # Use ageTags for junior filtering (matches UTR API)
    if filters.get('ageTags'):
        params['ageTags'] = filters['ageTags']
    
    if filters.get('nationality'):
        params['nationality'] = filters['nationality']
    if filters.get('max_age'):
        params['maxAge'] = filters['max_age']
    
    if filters.get('query'):
        params['query'] = filters['query']
    
    headers = {}
    if auth_info.get('token'):
        headers['Authorization'] = f"Bearer {auth_info['token']}"
    
    try:
        response = requests.get(SEARCH_URL, params=params, headers=headers, cookies=auth_info.get('cookies'))
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {'hits': []}

# ============================================
# EXTRACT PLAYER DATA (Basic Info from Search)
# ============================================
def extract_player(source):
    age_range = source.get('ageRange', '')
    age = source.get('age')
    
    # Pro Rank
    pro_rank = '-'
    rankings = source.get('thirdPartyRankings', [])
    if rankings:
        rank_obj = next((r for r in rankings if r.get('source') in ['ATP', 'WTA']), rankings[0] if rankings else None)
        if rank_obj:
            pro_rank = f"{rank_obj.get('source')} #{rank_obj.get('rank')}"
    
    # College
    college = '-'
    p_college = source.get('playerCollege')
    if p_college:
        college = p_college.get('name', '-') if isinstance(p_college, dict) else str(p_college)
    elif source.get('collegeRecruiting'):
        college = 'Recruiting'
    
    # Age display
    age_display = age or age_range or '-'
    if source.get('birthDate'):
        year = source['birthDate'].split('-')[0]
        age_display = f"{year} ({age_display})"
    
    return {
        'id': source.get('id'),
        'name': source.get('displayName') or f"{source.get('firstName')} {source.get('lastName')}",
        'utr': source.get('singlesUtr') or source.get('myUtrSingles') or 0,
        'doublesUtr': source.get('doublesUtr') or source.get('myUtrDoubles') or '',
        'trend': source.get('threeMonthRatingChangeDetails', {}).get('ratingDifference'),
        'age': age_display,
        'rawAge': age,
        'ageRange': age_range,
        'location': (source.get('location') or {}).get('display') or source.get('city') or '',
        'nationality': source.get('nationality'),
        'gender': 'M' if source.get('gender') == 'Male' else 'F' if source.get('gender') == 'Female' else source.get('gender'),
        'proRank': pro_rank,
        'college': college,
        'profileUrl': f"https://app.utrsports.net/profiles/{source.get('id')}",
        'hand': source.get('dominantHand') or '-',
        'backhand': source.get('backhand') or '-',
        'yearDelta': None,
        'winLoss': '-',
        'winPercent': '-',
        'upsetRatio': '-',
        # New KPIs
        'avgOppUtr': '-',
        'threeSetRecord': '-',
        'recentForm': '-',
        'tournamentCount': 0,
        'higherRatedWinPct': '-',
        'tiebreakRecord': '-',
        'comebackWins': 0,
        'peakUtr': '-',
        'minRating': '-'
    }

# ============================================
# FETCH PLAYER DETAILED METRICS
# ============================================
def fetch_player_metrics(auth_info, player):
    headers = {}
    if auth_info.get('token'):
        headers['Authorization'] = f"Bearer {auth_info['token']}"
    
    import datetime as dt
    one_year_ago = dt.datetime.now() - dt.timedelta(days=365)
    
    # DB Connection for this thread
    conn = tennis_db.get_connection()
    try:
        # 1. Fetch ALL Results (last 12 months) for metrics
        results_url = f"https://app.utrsports.net/api/v1/player/{player['id']}/results"

        # 1b. Fetch V2 Profile for Birth Date
        try:
            v2_url = f"https://app.utrsports.net/api/v2/player/{player['id']}"
            v2_res = requests.get(v2_url, headers=headers, cookies=auth_info.get('cookies'))
            if v2_res.status_code == 200:
                v2_data = v2_res.json()
                player['birthDate'] = v2_data.get('birthDate')
                # Always prefer V2 profile age as it is more accurate than search index
                if v2_data.get('age'):
                    player['rawAge'] = v2_data.get('age')
        except: pass
        
        # Counters for all metrics
        all_wins = 0
        all_losses = 0
        upsets = 0
        opponent_utrs = []
        
        # 3-set record
        three_set_wins = 0
        three_set_losses = 0
        
        # Recent form (last 10 matches by date)
        all_matches = []  # List of (date, won_bool)
        
        # Tournament count
        event_ids = set()
        
        # Higher-rated wins
        higher_rated_wins = 0
        higher_rated_matches = 0
        
        # Tiebreak record
        tiebreak_wins = 0
        tiebreak_losses = 0
        
        # Comeback wins (won after losing 1st set)
        comeback_wins = 0
        
        # Track player's UTR at each match for peak/min fallback
        player_utrs_in_matches = []
        
        # Paginate through results
        skip = 0
        batch_size = 100
        done = False
        
        while not done:
            r_params = {'top': batch_size, 'skip': skip}
            
            # Retry logic
            resp_res = None
            for attempt in range(3):
                try:
                    resp_res = requests.get(results_url, params=r_params, headers=headers, cookies=auth_info.get('cookies'))
                    if resp_res.status_code == 200:
                        break
                    elif resp_res.status_code == 429:
                        time.sleep(2 * (attempt + 1)) # Backoff
                except:
                    time.sleep(1)
            
            if not resp_res or resp_res.status_code != 200:
                print(f"Failed to fetch matches for {player['name']} (skip={skip})")
                break
            
            r_data = resp_res.json()
            events = r_data.get('events', [])
            
            if not events:
                break
            
            found_old = False
            for event in events:
                # Check event date
                event_date_str = event.get('startDate') or event.get('endDate')
                event_in_range = True
                if event_date_str:
                    try:
                        event_date = dt.datetime.fromisoformat(event_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                        # event_date < one_year_ago check removed for saving purposes
                        # found_old = True 
                        # event_in_range = False
                        pass
                    except:
                        pass
                
                # if not event_in_range:
                #    continue
                
                # Track unique events
                event_ids.add(event.get('id'))
                
                for draw in event.get('draws', []):
                    for result in draw.get('results', []):
                        # Check result date
                        result_date_str = result.get('date') or result.get('resultDate')
                        result_date = None
                        if result_date_str:
                            try:
                                result_date = dt.datetime.fromisoformat(result_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                                # if result_date < one_year_ago:
                                #     continue
                            except:
                                pass
                        
                        players_data = result.get('players', {})
                        winner = players_data.get('winner1', {})
                        loser = players_data.get('loser1', {})
                        score = result.get('score', {})
                        
                        player_id_str = str(player['id'])
                        is_winner = str(winner.get('id')) == player_id_str
                        is_loser = str(loser.get('id')) == player_id_str
                        
                        if not is_winner and not is_loser:
                            continue
                        
                        # Count sets
                        num_sets = len(score) if score else 0
                        is_three_set = num_sets >= 3
                        
                        # Check for tiebreaks
                        for set_key, set_data in (score or {}).items():
                            if set_data and set_data.get('tiebreak') is not None:
                                # There was a tiebreak in this set
                                winner_tb = set_data.get('winnerTiebreak', 0) or 0
                                loser_tb = set_data.get('tiebreak', 0) or 0
                                if is_winner:
                                    if winner_tb > loser_tb:
                                        tiebreak_wins += 1
                                    else:
                                        tiebreak_losses += 1
                                else:
                                    if loser_tb > winner_tb:
                                        tiebreak_wins += 1
                                    else:
                                        tiebreak_losses += 1
                        
                        # Check for comeback (lost 1st set but won match)
                        if is_winner and score and '1' in score:
                            first_set = score['1']
                            if first_set and first_set.get('winner', 0) < first_set.get('loser', 0):
                                comeback_wins += 1

                        # === SAVE MATCH TO DB ===
                        try:
                             # Save opponent
                             opp_obj = loser if is_winner else winner
                             if opp_obj and opp_obj.get('id'):
                                 opp_name = opp_obj.get('displayName') or f"{opp_obj.get('firstName', '')} {opp_obj.get('lastName', '')}".strip()
                                 if opp_name:
                                     tennis_db.save_player(conn, {
                                         'player_id': str(opp_obj.get('id')),
                                         'name': opp_name,
                                         'gender': PARAMS['GENDER'], # Assuming same gender for now, though mixed exists
                                         'utr_singles': opp_obj.get('singlesUtr'),
                                         'utr_doubles': opp_obj.get('doublesUtr')
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
                                 
                                 m_date = result_date or event_date if event_date_str else None
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
                            print(f"DB Error: {e_db}")
                            pass
                        # ========================
                        
                        # Only calculate metrics if within 1 year
                        if result_date and result_date < one_year_ago:
                            continue

                        if is_winner:
                            all_wins += 1
                            my_utr = winner.get('singlesUtr') or winner.get('utr') or 0
                            opp_utr = loser.get('singlesUtr') or loser.get('utr') or 0
                            
                            if opp_utr > 0:
                                opponent_utrs.append(opp_utr)
                            
                            # Upset: beat someone higher rated
                            if opp_utr > my_utr:
                                upsets += 1
                            
                            # Higher-rated opponent match
                            if opp_utr > my_utr:
                                higher_rated_wins += 1
                                higher_rated_matches += 1
                            elif opp_utr > 0 and my_utr > 0:
                                # Lower/equal rated - still count match if opp had rating
                                pass
                            
                            if is_three_set:
                                three_set_wins += 1
                            
                            # Track player's UTR at this match for peak/min fallback
                            if my_utr > 0:
                                player_utrs_in_matches.append(my_utr)
                            
                            all_matches.append((result_date or event_date if event_date_str else None, True))
                            
                        elif is_loser:
                            all_losses += 1
                            my_utr = loser.get('singlesUtr') or loser.get('utr') or 0
                            opp_utr = winner.get('singlesUtr') or winner.get('utr') or 0
                            
                            if opp_utr > 0:
                                opponent_utrs.append(opp_utr)
                            
                            # Lost to higher rated
                            if opp_utr > my_utr:
                                higher_rated_matches += 1
                            
                            if is_three_set:
                                three_set_losses += 1
                            
                            # Track player's UTR at this match for peak/min fallback
                            if my_utr > 0:
                                player_utrs_in_matches.append(my_utr)
                            
                            all_matches.append((result_date or event_date if event_date_str else None, False))
            
            # If all events in this batch are old, stop
            # removed optimize stop to ensure full history fetch
            # if found_old and len(events) > 0: ...
            
            skip += batch_size
            if skip >= 10000:
                done = True
            
            time.sleep(0.3) # Rate limit kindness
            
            # Commit the batch to release write locks before next network call
            try:
                conn.commit()
            except: pass
        
        # === Set all metrics ===
        
        # Win/Loss Record
        player['winLoss'] = f"{all_wins}W-{all_losses}L"
        total = all_wins + all_losses
        if total > 0:
            player['winPercent'] = f"{(all_wins/total)*100:.1f}%"
        
        # Upset Ratio
        if all_wins > 0:
            player['upsetRatio'] = f"{upsets}/{all_wins} ({upsets/all_wins:.0%})"
        else:
            player['upsetRatio'] = "0/0"
        
        # Average Opponent UTR
        if opponent_utrs:
            avg_opp = sum(opponent_utrs) / len(opponent_utrs)
            player['avgOppUtr'] = f"{avg_opp:.2f}"
        
        # 3-Set Record
        three_set_total = three_set_wins + three_set_losses
        if three_set_total > 0:
            pct = (three_set_wins / three_set_total) * 100
            player['threeSetRecord'] = f"{three_set_wins}W-{three_set_losses}L ({pct:.0f}%)"
        else:
            player['threeSetRecord'] = "0-0"
        
        # Recent Form (Last 10)
        # Sort by date descending
        all_matches_sorted = sorted([m for m in all_matches if m[0]], key=lambda x: x[0], reverse=True)
        last_10 = all_matches_sorted[:10]
        if last_10:
            recent_wins = sum(1 for m in last_10 if m[1])
            recent_losses = len(last_10) - recent_wins
            player['recentForm'] = f"{recent_wins}W-{recent_losses}L"
        
        # Tournament Count
        player['tournamentCount'] = len(event_ids)
        
        # Higher-Rated Win %
        if higher_rated_matches > 0:
            hr_pct = (higher_rated_wins / higher_rated_matches) * 100
            player['higherRatedWinPct'] = f"{higher_rated_wins}/{higher_rated_matches} ({hr_pct:.0f}%)"
        else:
            player['higherRatedWinPct'] = "N/A"
        
        # Tiebreak Record
        tb_total = tiebreak_wins + tiebreak_losses
        if tb_total > 0:
            tb_pct = (tiebreak_wins / tb_total) * 100
            player['tiebreakRecord'] = f"{tiebreak_wins}W-{tiebreak_losses}L ({tb_pct:.0f}%)"
        else:
            player['tiebreakRecord'] = "0-0"
        
        # Comeback Wins
        player['comebackWins'] = comeback_wins
        
        # Calculate Peak/Min from match data as fallback
        if player_utrs_in_matches:
            player['peakUtr'] = max(player_utrs_in_matches)
            player['minRating'] = min(player_utrs_in_matches)
        
        # 2. Fetch Stats for Year Delta (History) - but validate data is current
        stats_url = f"https://app.utrsports.net/api/v1/player/{player['id']}/stats"
        params = {
            'type': 'singles',
            'resultType': 'verified', 
            'Months': 12
        }
        resp = requests.get(stats_url, params=params, headers=headers, cookies=auth_info.get('cookies'))
        
        if resp.status_code == 200:
            data = resp.json()
            
            # Check if stats data is current (subtitle should contain current year)
            subtitle = data.get('subtitle', '')
            current_year = str(dt.datetime.now().year)
            stats_is_current = current_year in subtitle or str(int(current_year) - 1) in subtitle
            
            # Only use stats API peak/min if data is current and has values
            if stats_is_current:
                if data.get('maxRating') and (player['peakUtr'] == '-' or data.get('maxRating') > player.get('peakUtr', 0)):
                    player['peakUtr'] = data.get('maxRating')
                if data.get('minRating') and (player['minRating'] == '-' or data.get('minRating') < player.get('minRating', 100)):
                    player['minRating'] = data.get('minRating')
            
            # Year Delta (History)
            history = data.get('extendedRatingProfile', {}).get('history') or data.get('ratingHistory', [])
            if history:
                current_rating = player['utr']
                prior_rating = None
                closest_diff = float('inf')
                
                for entry in history:
                    try:
                        entry_date = dt.datetime.fromisoformat(entry['date'].replace('Z', '+00:00')).replace(tzinfo=None)
                        diff = abs((entry_date - one_year_ago).total_seconds())
                        if diff < closest_diff:
                            closest_diff = diff
                            prior_rating = entry.get('rating')
                    except:
                        continue
                
                if prior_rating is not None and prior_rating > 0 and closest_diff < (60 * 24 * 3600):
                    player['yearDelta'] = round(current_rating - prior_rating, 2)
                
                # SAVE HISTORY TO DB
                try:
                    for h_item in history:
                        if h_item.get('rating') and h_item.get('date'):
                            # Format date if needed, UTR sends ISO string (e.g. 2023-01-01T00:00:00Z)
                            tennis_db.save_history(conn, {
                                'player_id': str(player['id']),
                                'date': h_item.get('date'),
                                'rating': h_item.get('rating'),
                                'type': 'singles'
                            })
                except: pass
                
    except Exception as e:
        print(f"Error fetching stats for {player['name']}: {e}")
        pass
    
    # === SAVE TO DB (Player Profile) ===
    try:
        # Save Player
        # Ensure we have a valid ID and Name
        if player.get('id'):
            p_data = {
                'player_id': str(player['id']),
                'name': player.get('name'),
                'college': player.get('college'),
                'country': player.get('nationality'),
                'country': player.get('nationality'),
                'gender': player.get('gender') or PARAMS['GENDER'], # Use detected gender, fallback to param
                'utr_singles': player.get('utr'),
                'utr_doubles': player.get('doublesUtr'),
                'utr_doubles': player.get('doublesUtr'),
                'age': player.get('rawAge'),
                'birth_date': player.get('birthDate'),
                'location': player.get('location'),
                'pro_rank': player.get('proRank'),
                'age_group': player.get('ageRange'),
                'comeback_wins': comeback_wins,
                'year_delta': player.get('yearDelta'),
                'tiebreak_wins': tiebreak_wins,
                'tiebreak_losses': tiebreak_losses,
                'three_set_wins': three_set_wins,
                'three_set_losses': three_set_losses
            }
            tennis_db.save_player(conn, p_data)
    except: pass
    
    finally:
        if conn:
            try:
                conn.commit()
            except: pass
            conn.close()


# ============================================
# MAIN
# ============================================
def main():
    print("================================================================")
    print("          UTR PLAYER SCRAPER (Multi-Country Merge)")
    print("================================================================")
    print(f"Country={PARAMS['COUNTRY']}, Gender={PARAMS['GENDER']}, Category={PARAMS['CATEGORY']}, Count={PARAMS['TOP_COUNT']}\n")
    
    auth_info = login()
    tennis_db.init_db() # Initialize DB
    target_count = PARAMS['TOP_COUNT']
    all_players = []
    seen_ids = set()
    
    # Determine search mode: ALL (global via countries), MAJOR (40 countries), or specific country
    is_global_search = PARAMS['COUNTRY'] == 'ALL' or PARAMS['COUNTRY'] == ''
    is_major_search = PARAMS['COUNTRY'] == 'MAJOR'
    
    if PARAMS['PLAYER']:
        print(f"Searching for player: {PARAMS['PLAYER']}...\n")
        # For name search, we relax other filters but keep gender if specified
        filters = {
            'query': PARAMS['PLAYER'],
            'top': 20
        }
        if PARAMS['GENDER'] and PARAMS['GENDER'] in ['M', 'F'] and '--gender' in sys.argv:
             filters['gender'] = PARAMS['GENDER']
             
        results = search_players(auth_info, filters)
        hits = results.get('hits', []) or results.get('players', [])
        
        if not hits:
            print(f"No results found for '{PARAMS['PLAYER']}'.")
            return
            
        for hit in hits:
            source = hit.get('source', hit)
            player = extract_player(source)
            # If searching by name, we might want to see all results regardless of category
            # but we'll apply categorical filtering if it's explicitly 'junior'
            if PARAMS['CATEGORY'] == 'junior':
                if player['rawAge'] and player['rawAge'] > 18:
                    continue
            
            all_players.append(player)
        
        print(f"Found {len(all_players)} matching players.")

    elif is_global_search or is_major_search:
        countries = MAJOR_TENNIS_COUNTRIES
        if is_global_search:
            print(f"Searching {len(MAJOR_TENNIS_COUNTRIES)} countries for GLOBAL top players...\n")
        elif is_major_search:
            print(f"Searching {len(MAJOR_TENNIS_COUNTRIES)} major tennis countries...\n")
        
        for country in countries:
            sys.stdout.write(f"Searching {country}... ")
            sys.stdout.flush()
            
            # Use UTR banding to get more results
            utr_bands = [
                {'min': 10, 'max': 16.5},
                {'min': 9, 'max': 10},
                {'min': 8, 'max': 9},
                {'min': 7, 'max': 8},
                {'min': 6, 'max': 7},
                {'min': 5, 'max': 6},
                {'min': 1, 'max': 5}
            ]
            
            country_added = 0
            
            for band in utr_bands:
                filters = {
                    'nationality': country,
                    'gender': PARAMS['GENDER'],
                    'min_utr': band['min'],
                    'max_utr': band['max'],
                    'ageTags': 'U18' if PARAMS['CATEGORY'] == 'junior' else None,
                    'top': 100
                }
                
                results = search_players(auth_info, filters)
                hits = results.get('hits', []) or results.get('players', [])
                
                for hit in hits:
                    source = hit.get('source', hit)
                    if source.get('id') in seen_ids:
                        continue
                    
                    player = extract_player(source)
                    
                    # Category filter
                    if PARAMS['CATEGORY'] == 'junior':
                        if player['rawAge'] and player['rawAge'] > 18:
                            continue
                        if not player['rawAge'] and player['ageRange']:
                            import re
                            if re.match(r'^(19|2|3|4|5)', player['ageRange']):
                                continue
                    
                    seen_ids.add(source.get('id'))
                    all_players.append(player)
                    country_added += 1
            
            print(f"{country_added} players")
    else:
        print(f"Searching country: {PARAMS['COUNTRY']}...\n")
        countries = [PARAMS['COUNTRY']]
        for country in countries:
            sys.stdout.write(f"Searching {country}... ")
            sys.stdout.flush()
            
            # Use UTR banding to get more results
            utr_bands = [
                {'min': 10, 'max': 16.5},
                {'min': 9, 'max': 10},
                {'min': 8, 'max': 9},
                {'min': 7, 'max': 8},
                {'min': 6, 'max': 7},
                {'min': 5, 'max': 6},
                {'min': 1, 'max': 5}
            ]
            
            country_added = 0
            
            for band in utr_bands:
                filters = {
                    'nationality': country,
                    'gender': PARAMS['GENDER'],
                    'min_utr': band['min'],
                    'max_utr': band['max'],
                    'ageTags': 'U18' if PARAMS['CATEGORY'] == 'junior' else None,
                    'top': 100
                }
                
                results = search_players(auth_info, filters)
                hits = results.get('hits', []) or results.get('players', [])
                
                for hit in hits:
                    source = hit.get('source', hit)
                    if source.get('id') in seen_ids:
                        continue
                    
                    player = extract_player(source)
                    
                    # Category filter
                    if PARAMS['CATEGORY'] == 'junior':
                        if player['rawAge'] and player['rawAge'] > 18:
                            continue
                        if not player['rawAge'] and player['ageRange']:
                            import re
                            if re.match(r'^(19|2|3|4|5)', player['ageRange']):
                                continue
                    
                    seen_ids.add(source.get('id'))
                    all_players.append(player)
                    country_added += 1
            
            print(f"{country_added} players")
    
    # Sort by UTR descending
    all_players.sort(key=lambda x: x.get('utr') or 0, reverse=True)
    
    # Limit to top N
    final_players = all_players[:target_count]
    
    # Fetch detailed metrics (Stats + History + Upsets)
    print(f"\nFetching detailed metrics (Record, History, Upsets) for top {len(final_players)} players...")
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        total = len(final_players)
        for i, _ in enumerate(executor.map(lambda p: fetch_player_metrics(auth_info, p), final_players)):
            sys.stdout.write(f"\rProgress: {i+1}/{total}    ")
            sys.stdout.flush()
    print("\nMetrics fetch complete.\n")
    
    print(f"\nCollected {len(all_players)} total players, selecting top {len(final_players)}")
    
    # Display top 20
    print('\n' + '=' * 130)
    country_label = 'WORLD' if PARAMS['COUNTRY'] == 'ALL' else PARAMS['COUNTRY']
    gender_label = 'GIRLS' if PARAMS['GENDER'] == 'F' else 'BOYS'
    print(f"TOP {len(final_players)} {PARAMS['CATEGORY'].upper()} {gender_label} ({country_label})")
    print('=' * 130)
    
    # Header
    print(f"{'#'.rjust(3)} {'Name'.ljust(25)} {'UTR'.ljust(6)} {'Dbls'.ljust(6)} {'1Y'.ljust(6)} {'Record'.ljust(10)} {'Win%'.ljust(6)} {'Upsets'.ljust(12)} {'Hand'.ljust(6)}")
    print('-' * 130)
    
    for i, p in enumerate(final_players[:20]):
        delta_str = f"{p['yearDelta']:+g}" if p['yearDelta'] is not None else '-'
        print(f"{str(i+1).rjust(3)} {p['name'][:25].ljust(25)} {str(p['utr']).ljust(6)} {str(p['doublesUtr']).ljust(6)} {delta_str.ljust(6)} {p['winLoss'].ljust(10)} {p['winPercent'].ljust(6)} {p['upsetRatio'].ljust(12)} {p['hand'][:6]}")
    
    if len(final_players) > 20:
        print(f"    ... and {len(final_players) - 20} more")
    
    # Save CSV
    date_str = datetime.now().strftime("%Y%m%d")
    country_str = 'World' if (PARAMS['COUNTRY'] == 'ALL' or PARAMS['COUNTRY'] == '') else PARAMS['COUNTRY']
    gender_str = 'Male' if PARAMS['GENDER'] == 'M' else 'Female'
    import os
    os.makedirs('output', exist_ok=True)
    filename = os.path.join('output', f"{country_str}_{PARAMS['CATEGORY']}_{gender_str}_ANALYST_{date_str}.csv")
    
    headers = [
        'Rank', 'Name', 'Singles UTR', 'Doubles UTR', 'Peak UTR', 'Min Rating',
        '3-Month Trend', '1-Year Delta', 'Win Record', 'Win %', 'Upset Ratio',
        'Avg Opp UTR', '3-Set Record', 'Recent Form (L10)', 'Tournaments',
        'vs Higher Rated', 'Tiebreak Record', 'Comeback Wins',
        'Age', 'Country', 'Location', 'Pro Rank', 'Profile URL'
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for i, p in enumerate(final_players):
            trend = f"{p['trend']:.2f}" if p['trend'] is not None else ''
            delta_val = p['yearDelta'] if p['yearDelta'] is not None else ''
            writer.writerow([
                i + 1,
                p['name'],
                p['utr'],
                p['doublesUtr'],
                p['peakUtr'],
                p['minRating'],
                trend,
                delta_val,
                p['winLoss'],
                p['winPercent'],
                p['upsetRatio'],
                p['avgOppUtr'],
                p['threeSetRecord'],
                p['recentForm'],
                p['tournamentCount'],
                p['higherRatedWinPct'],
                p['tiebreakRecord'],
                p['comebackWins'],
                p['age'],
                p['nationality'] or '',
                p['location'],
                p['proRank'],
                p['profileUrl']
            ])
    
    print(f"\nSaved to: {filename}")
    print(f"Done! {len(final_players)} players scraped.")

if __name__ == "__main__":
    main()
