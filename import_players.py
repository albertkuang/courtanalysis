
import requests
import sys
import argparse
import time
import tennis_db
import concurrent.futures
from config import UTR_CONFIG

# Configuration
CONFIG = UTR_CONFIG
LOGIN_URL = "https://app.utrsports.net/api/v1/auth/login"
SEARCH_URL = "https://app.utrsports.net/api/v2/search/players"

# Authentication
def login():
    print("Logging in to UTR...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Content-Type": "application/json"
    }
    try:
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
    except Exception as e:
        print(f"Login Error: {e}")
        sys.exit(1)

# Search Logic
def search_players(auth_info, filters):
    params = {
        'top': filters.get('top', 100),
        'skip': filters.get('skip', 0),
        'gender': filters.get('gender'),
        'utrMin': filters.get('min_utr', 1),
        'utrMax': filters.get('max_utr', 16.5),
        'nationality': filters.get('nationality', 'CAN'), # Default to Canada
    }
    
    # Only set utrType if specifically requested (allows finding all players)
    if filters.get('utrType'):
        params['utrType'] = filters.get('utrType')
    
    if filters.get('ageTags'):
        params['ageTags'] = filters['ageTags']
        
    headers = {'Authorization': f"Bearer {auth_info['token']}"}
    
    try:
        response = requests.get(SEARCH_URL, params=params, headers=headers, cookies=auth_info.get('cookies'))
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  Search returned status {response.status_code}")
    except Exception as e:
        print(f"Search Error: {e}")
    return {'hits': []}

# Process and Save Player - Full Metrics
def get_v2_profile(auth_info, player_id):
    headers = {'Authorization': f"Bearer {auth_info['token']}"}
    try:
        v2_url = f"https://app.utrsports.net/api/v2/player/{player_id}"
        v2_res = requests.get(v2_url, headers=headers, cookies=auth_info.get('cookies'))
        if v2_res.status_code == 200:
            return v2_res.json()
    except: pass
    return None

def process_player(auth_info, source, display_only=False):
    """
    Extracts basic info, fetches detailed V2 profile, Calculates ALL Metrics (Stats + Matches), and saves to DB.
    """
    conn = tennis_db.get_connection()
    try:
        player_id = str(source.get('id'))
        name = source.get('displayName') or f"{source.get('firstName')} {source.get('lastName')}"
        
        # 1. Basic Info (from source initially, will be updated by V2)
        age_range = source.get('ageRange', '')
        search_age = source.get('age')
        
        player_data = {
            'player_id': player_id,
            'name': name,
            'country': source.get('nationality'),
            'gender': source.get('gender'), 
            'utr_singles': source.get('singlesUtr') or source.get('myUtrSingles') or 0,
            'utr_doubles': source.get('doublesUtr') or source.get('myUtrDoubles') or 0,
            'location': (source.get('location') or {}).get('display') or source.get('city'),
            'age_group': age_range,
            'age': search_age,
            'birth_date': None, # Will be updated by V2
            'college_name': None,
            'college_id': None,
            'grad_year': None,
            'is_active_college': False
        }
        
        # normalize gender
        if player_data['gender'] == 'Male': player_data['gender'] = 'M'
        elif player_data['gender'] == 'Female': player_data['gender'] = 'F'

        headers = {'Authorization': f"Bearer {auth_info['token']}"}
        
        # 2. Fetch V2 Profile (Accurate Age/DOB)
        v2 = get_v2_profile(auth_info, player_id)
        if v2:
             player_data['birth_date'] = v2.get('birthDate')
             if v2.get('age'):
                 player_data['age'] = v2.get('age')
             if v2.get('location') and isinstance(v2.get('location'), dict):
                 player_data['location'] = v2.get('location').get('display')
                 
             # Update UTRs from V2 if search was 0
             if not player_data['utr_singles']:
                 player_data['utr_singles'] = v2.get('singlesUtr') or 0
             if not player_data['utr_doubles']:
                  player_data['utr_doubles'] = v2.get('doublesUtr') or 0

             # --- College Data Extraction ---
             player_college = v2.get('playerCollege')
             college_details = v2.get('playerCollegeDetails')
                
             college_name = None
             college_id = None
             grad_year = None
             is_active_college = False

             if player_college:
                 college_name = player_college.get('name') or player_college.get('displayName')
                 college_id = player_college.get('id')
             
             if college_details:
                 grad_year = college_details.get('gradYear')
             elif v2.get('gradYearCollege'):
                 grad_year = v2.get('gradYearCollege')

             # Determine if active college player
             # Logic: Has a college assigned AND grad year is in future (or very recent)
             # Also check primaryTags for "College"
             tags = v2.get('primaryTags', [])
             is_college_tag = 'College' in tags
                
             from datetime import datetime
             current_year = datetime.now().year
             
             if college_name and grad_year:
                 try:
                     # Handle ISO date string
                     gy_str = str(grad_year)[:4]
                     gy_int = int(gy_str)
                     # Active if grad year is this year or future
                     if gy_int >= current_year:
                         is_active_college = True
                 except:
                     pass
                     
             # TRUST THE TAG: If UTR says they are College, they are likely active (or recently active)
             # Our research shows Ben Shelton (Alumni) does NOT have the tag, while Murphy Cassone (Grad 2024) DOES.
             if is_college_tag and not is_active_college:
                 is_active_college = True
 
             player_data['college_name'] = college_name
             player_data['college_id'] = college_id
             player_data['grad_year'] = grad_year
             player_data['is_active_college'] = is_active_college

        # Check Adult UTR >= 5 filter with updated data
        # Check source if category is not passed here? 
        # We need to know category. It's not passed to process_player currently.
        # However, for this specific user request, we know we are running in adult context if we are running the script.
        # But process_player is generic. 
        # Actually, let's just do it if either we passed a flag or inferred it.
        # For now, let's rely on checking if the caller wanted to filter. 
        # But wait, the caller (scan_band) passed us.
        
        # NOTE: We adding a hacky check or we update signature?
        # Let's inspect 'age_group' or just strictly check UTR if it seems like an adult import?
        # Better: Assume caller handled "Search" filtering, but "Zero UTR" cases slipped through.
        # So if UTR is STILL < 5 (and not 0? or even 0?), we might skip.
        # If UTR < 5.0 and > 0, we typically skip for Adults.
        # Let's filter here if it's low.
        
        if display_only:
            # If UTR is low (valid but low), maybe we shouldn't display it if the user wants filtered view?
            # User asked "only take utr over 5".
            if player_data['utr_singles'] and player_data['utr_singles'] < 5.0:
                 return # Skip display/save
            
            print(f"\n[DISPLAY ONLY] Player: {player_data['name']}")
            print(f"  ID: {player_data['player_id']}")
            print(f"  UTR: {player_data['utr_singles']}")
            print(f"  Age: {player_data.get('age')} (Group: {player_data.get('age_group')})")
            print(f"  Location: {player_data.get('location')}")
            return

        try:
            results_url = f"https://app.utrsports.net/api/v1/player/{player_id}/results"
            r_params = {'top': 100} # Analyzer uses up to 1000, 100 is decent sample for update
            r_res = requests.get(results_url, params=r_params, headers=headers, cookies=auth_info.get('cookies'))
            
            comeback_wins = 0
            tiebreak_wins = 0
            tiebreak_losses = 0
            three_set_wins = 0
            three_set_losses = 0
            wins = 0
            losses = 0
            
            if r_res.status_code == 200:
                r_data = r_res.json()
                events = r_data.get('events', [])
                
                for event in events:
                    for draw in event.get('draws', []):
                        for result in draw.get('results', []):
                            winner = result.get('players', {}).get('winner1', {})
                            loser = result.get('players', {}).get('loser1', {})
                            score = result.get('score', {})
                            
                            is_winner = str(winner.get('id')) == player_id
                            is_loser = str(loser.get('id')) == player_id
                            
                            if not is_winner and not is_loser: continue
                            
                            if is_winner: wins += 1
                            if is_loser: losses += 1
                            
                            # Count sets
                            num_sets = len(score) if score else 0
                            is_three_set = num_sets >= 3
                            
                            if is_three_set:
                                if is_winner: three_set_wins += 1
                                else: three_set_losses += 1
                            
                            # Check Tiebreaks
                            for set_key, set_data in (score or {}).items():
                                if set_data and set_data.get('tiebreak') is not None:
                                    winner_tb = set_data.get('winnerTiebreak', 0) or 0
                                    loser_tb = set_data.get('tiebreak', 0) or 0
                                    if is_winner:
                                        if winner_tb > loser_tb: tiebreak_wins += 1
                                        else: tiebreak_losses += 1
                                    else:
                                        if loser_tb > winner_tb: tiebreak_wins += 1
                                        else: tiebreak_losses += 1
    
                            # Check Comeback (Winner lost 1st set)
                            if is_winner and score and '1' in score:
                                first_set = score['1']
                                if first_set and first_set.get('winner', 0) < first_set.get('loser', 0):
                                    comeback_wins += 1
                                    
            player_data['comeback_wins'] = comeback_wins
            player_data['tiebreak_wins'] = tiebreak_wins
            player_data['tiebreak_losses'] = tiebreak_losses
            player_data['three_set_wins'] = three_set_wins
            player_data['three_set_losses'] = three_set_losses
            
        except Exception as e:
            pass
    
        # 4. Fetch Stats (1-Year Delta)
        try:
            import datetime as dt
            one_year_ago = dt.datetime.now() - dt.timedelta(days=365)
            
            stats_url = f"https://app.utrsports.net/api/v1/player/{player_id}/stats"
            params = {'type': 'singles', 'resultType': 'verified', 'Months': 12}
            stats_res = requests.get(stats_url, params=params, headers=headers, cookies=auth_info.get('cookies'))
            
            if stats_res.status_code == 200:
                s_data = stats_res.json()
                history = s_data.get('extendedRatingProfile', {}).get('history') or s_data.get('ratingHistory', [])
                
                if history and player_data['utr_singles']:
                    current_rating = player_data['utr_singles']
                    prior_rating = None
                    closest_diff = float('inf')
                    
                    for entry in history:
                        try:
                            entry_date = dt.datetime.fromisoformat(entry['date'].replace('Z', '+00:00')).replace(tzinfo=None)
                            diff = abs((entry_date - one_year_ago).total_seconds())
                            if diff < closest_diff:
                                closest_diff = diff
                                prior_rating = entry.get('rating')
                        except: continue
                    
                    if prior_rating is not None:
                        # Filter out big jumps that might be data errors if needed, but for now take raw
                        player_data['year_delta'] = round(current_rating - prior_rating, 2)
                        
        except: pass
    
        # 5. Save to DB
        tennis_db.save_player(conn, player_data)
        conn.commit()
    except Exception as ie:
        print(f"Error saving {source.get('displayName')}: {ie}")
    finally:
        conn.close()

def import_players(country='CAN', category='junior', max_workers=5, display_only=False):
    auth_info = login()
    tennis_db.init_db()
    conn = tennis_db.get_connection()
    
    print(f"\nStarting import for Country: {country}, Category: {category}")
    print(f"Concurrent Workers: {max_workers}")
    
    # Define search strategy
    genders = ['M', 'F']
    
    # UTR Bands - smaller increments for better coverage (API may limit results per query)
    if category == 'adult':
        utr_bands = [
            {'min': 13, 'max': 16.5},
            {'min': 11.5, 'max': 13},
            {'min': 10, 'max': 11.5},
            {'min': 9, 'max': 10},
            {'min': 8, 'max': 9},
            {'min': 7, 'max': 8},
            {'min': 6, 'max': 7},
            {'min': 5, 'max': 6}
        ]
    else:
        utr_bands = [
            {'min': 13, 'max': 16.5},
            {'min': 11.5, 'max': 13},
            {'min': 10, 'max': 11.5},
            {'min': 9, 'max': 10},
            {'min': 8, 'max': 9},
            {'min': 7, 'max': 8},
            {'min': 6, 'max': 7},
            {'min': 5, 'max': 6},
            {'min': 4, 'max': 5},
            {'min': 3, 'max': 4},
            {'min': 1, 'max': 3}
        ]
    
    total_processed = 0
    seen_ids = set()

    # Support comma-separated countries
    country_list = country.split(',')
    
    for c_code in country_list:
        c_code = c_code.strip().upper()
        if not c_code: continue
        
        print(f"\n====== Processing Country: {c_code} Category: {category} ======")

        def scan_band_for_country(band_min, band_max, gender, target_country):
            nonlocal total_processed
            
            filters = {
                'gender': gender,
                'min_utr': band_min,
                'max_utr': band_max,
                'top': 100,
                'skip': 0,
                'utrType': 'verified'
            }
            
            # Handle 'ALL' or specific country
            if target_country and target_country != 'ALL':
                filters['nationality'] = target_country
            
            if category == 'junior':
                filters['ageTags'] = 'U18'
            elif category == 'college':
                filters['primaryTags'] = 'College'
                
            results = search_players(auth_info, filters)
            hits = results.get('hits', []) or results.get('players', [])
            total_in_band = results.get('total', 0)
            
            # Recursive splitting
            if total_in_band > 100 and (band_max - band_min) > 0.01:
                mid = round((band_min + band_max) / 2, 3)
                print(f"    Band {band_min}-{band_max} has {total_in_band} players. Splitting at {mid}...")
                scan_band_for_country(band_min, mid, gender, target_country)
                scan_band_for_country(mid, band_max, gender, target_country)
                return
    
            print(f"    Scanning UTR {band_min} - {band_max} ({total_in_band} players)...")
            
            batch_players = []
            for hit in hits:
                source = hit.get('source', hit)
                pid = str(source.get('id'))
                
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)
                
                # Filters (keeping existing logic)
                if category == 'junior':
                    age_range = source.get('ageRange')
                    if age_range and (age_range.startswith('19') or age_range.startswith('2') or age_range.startswith('3') or age_range.startswith('4')):
                         continue
    
                if category == 'adult':
                     s_utr = source.get('singlesUtr') or source.get('myUtrSingles') or 0
                     if s_utr > 0 and s_utr < 5.0:
                         continue
    
                if not display_only:
                    c = conn.cursor()
                    c.execute("SELECT 1 FROM players WHERE player_id = ?", (pid,))
                    if c.fetchone():
                        continue
                
                batch_players.append(source)
            
            if batch_players:
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as batch_executor:
                    futures = [batch_executor.submit(process_player, auth_info, p, display_only) for p in batch_players]
                    for future in concurrent.futures.as_completed(futures):
                        total_processed += 1
                        if not display_only and total_processed % 10 == 0:
                            sys.stdout.write(f"\rTotal Processed: {total_processed}...")
                            sys.stdout.flush()

        for gender in genders:
            print(f"\n--- Processing Gender: {gender} ---")
            seen_ids = set() 
            for band in utr_bands:
                scan_band_for_country(band['min'], band['max'], gender, c_code)


    print(f"\n\nImport Complete! Total players processed: {total_processed}")


def search_player_by_name(name, country='CAN'):
    """Search for a specific player by name for debugging."""
    auth_info = login()
    
    SEARCH_URL = "https://app.utrsports.net/api/v2/search/players"
    headers = {'Authorization': f"Bearer {auth_info['token']}"}
    
    params = {
        'query': name,
        'top': 20,
        'nationality': country
    }
    
    try:
        response = requests.get(SEARCH_URL, params=params, headers=headers, cookies=auth_info.get('cookies'))
        if response.status_code == 200:
            results = response.json()
            hits = results.get('hits', []) or results.get('players', [])
            
            print(f"\n=== Search Results for '{name}' ===")
            print(f"Total found: {results.get('total', len(hits))}")
            
            for i, hit in enumerate(hits[:10]):
                source = hit.get('source', hit)
                # Instead of printing raw, process it to get V2 data if needed
                process_player(auth_info, source, display_only=True)
            
            if len(hits) > 0:
                # Try to import the first match
                first = hits[0].get('source', hits[0])
                print(f"\n--- Importing first match: {first.get('displayName')} ---")
                tennis_db.init_db()
                process_player(auth_info, first)
                print("Done!")
            return hits
    except Exception as e:
        print(f"Search Error: {e}")
    return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Import Players Detailed Info (No Matches)')
    parser.add_argument('--country', default='CAN', help='Country Code (default: CAN)')
    parser.add_argument('--category', default='junior', help='Category (junior, adult, college)')
    parser.add_argument('--workers', type=int, default=10, help='Concurrent requests (default: 10)')
    parser.add_argument('--name', type=str, help='Search and import specific player by name')
    parser.add_argument('--display-only', action='store_true', help='Only display player info, do not save to DB')

    args = parser.parse_args()
    
    if args.name:
        search_player_by_name(args.name, args.country)
    else:
        # Pass display_only to import_players
        # We need to update import_players signature first
        import_players(args.country, args.category, args.workers, display_only=args.display_only)
