
import requests
import sys
import argparse
import time
import tennis_db
import concurrent.futures
from config import UTR_CONFIG
from datetime import datetime

# Configuration
CONFIG = UTR_CONFIG
LOGIN_URL = "https://app.utrsports.net/api/v1/auth/login"

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
        
        # If no JWT token, use cookies for authentication (UTR now uses MFA)
        if not token:
            print("Note: No JWT token returned (MFA may be required). Using cookies for auth.")
        
        return {'token': token, 'cookies': response.cookies}
    except Exception as e:
        print(f"Login Error: {e}")
        sys.exit(1)

def fetch_and_save_history(auth_info, player_row):
    """
    Fetches rating history for a player and saves to 'utr_history' table.
    Now searches UTR by name to get the correct player ID.
    Includes fallback to reconstructing history from match results.
    """
    player_id = str(player_row['player_id'])
    name = player_row['name']
    
    conn = tennis_db.get_connection()
    history = None
    
    # Build headers - handle case where token is None
    headers = {}
    if auth_info.get('token'):
        headers['Authorization'] = f"Bearer {auth_info['token']}"
    headers['User-Agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    
    # First, try to find the player in UTR by name to get the correct ID
    search_url = "https://app.utrsports.net/api/v2/search/players"
    search_params = {'query': name, 'top': 5}
    precise_rating = None
    print(f"DEBUG: Searching UTR for {name} (Initial ID: {player_id})")
    try:
        search_res = requests.get(search_url, params=search_params, headers=headers, cookies=auth_info.get('cookies'), timeout=15)
        if search_res.status_code == 200:
            search_data = search_res.json()
            hits = search_data.get('hits', [])
            print(f"DEBUG: Found {len(hits)} search hits")
            for hit in hits:
                source = hit.get('source', hit)
                first = source.get('firstName') or ''
                last = source.get('lastName') or ''
                disp = source.get('displayName') or ''
                hit_name = disp or f"{first} {last}".strip()
                print(f"DEBUG: Hit: '{hit_name}' (ID: {hit.get('id')})")
                
                if name.lower() in hit_name.lower():
                    # Found matching player - use this ID
                    new_player_id = str(hit.get('id'))
                    
                    # Capture precise CURRENT rating from search hit
                    p_utr = source.get('myUtrSingles') or source.get('singlesUtr')
                    if p_utr and p_utr > 0:
                        precise_rating = p_utr
                        print(f"DEBUG: Captured precise UTR {precise_rating} from search hit")
                    
                    if new_player_id != player_id:
                        print(f"Note: Found UTR ID {new_player_id} for {name} (DB ID: {player_id})")
                    player_id = new_player_id
                    break
        else:
            print(f"DEBUG: Search failed with status {search_res.status_code}")
    except Exception as e:
        print(f"DEBUG: Search error: {e}")
        pass
    
    try:
        # 1. Fetch UTR History via stats endpoint
        stats_url = f"https://app.utrsports.net/api/v1/player/{player_id}/stats"
        
        for t in ['singles', 'doubles']:
            if history: break
            for rt in ['verified', 'myutr']:
                if history: break
                for m in [12, 6, 24, 36, 60, 120]:
                    params = {'type': t, 'resultType': rt, 'Months': m}
                    print(f"DEBUG: Trying type={t}, rt={rt}, m={m} for player {player_id}")
                    try:
                        res = requests.get(stats_url, params=params, headers=headers, cookies=auth_info.get('cookies'), timeout=15)
                        if res.status_code == 200:
                            s_data = res.json()
                            
                            # Check for Federer default (ID 3456 or rating 16.02 when not expected)
                            cur_r = s_data.get('currentRating')
                            if cur_r == 16.02 and player_id != "3456":
                                print(f"DEBUG: Caught Federer redirect for {player_id}. Skipping stats.")
                                break # Move to next type/rt

                            ext_p = s_data.get('extendedRatingProfile') or {}
                            history = ext_p.get('history') or s_data.get('ratingHistory', [])
                            
                            # Fallback to trend chart points if history list is empty
                            if not history:
                                trend_chart = s_data.get('ratingTrendChart') or {}
                                if trend_chart.get('points'):
                                    print(f"DEBUG: Found {len(trend_chart['points'])} points in trend chart")
                                    history = [{'date': p.get('date'), 'rating': p.get('rating')} for p in trend_chart['points']]

                            if history and len(history) > 0:
                                print(f"DEBUG: Success with type={t}, rt={rt}, m={m}")
                                break
                    except Exception as e:
                        print(f"DEBUG: Error in request: {e}")
                        continue
        
        # 2. If still no history from stats, try profile endpoint
        if not history:
            print("DEBUG: No history in stats, trying profile endpoint")
            profile_urls = [
                f"https://app.utrsports.net/api/v2/player/{player_id}",
                f"https://app.utrsports.net/api/v1/player/{player_id}/profile"
            ]
            for p_url in profile_urls:
                try:
                    profile_res = requests.get(p_url, headers=headers, cookies=auth_info.get('cookies'), timeout=15)
                    if profile_res.status_code == 200:
                        profile_data = profile_res.json()
                        
                        # Capture precise rating
                        if not precise_rating:
                            p_utr = profile_data.get('myUtrSingles') or profile_data.get('singlesUtr')
                            if p_utr and p_utr > 0:
                                precise_rating = p_utr
                                print(f"DEBUG: Captured precise UTR {precise_rating} from profile hit")

                        ext_profile = profile_data.get('extendedRatingProfile') or {}
                        history = ext_profile.get('history') or profile_data.get('ratingHistory', [])
                        if history:
                            print(f"DEBUG: Found history in profile endpoint: {p_url}")
                            break
                except: pass

        # 3. Fallback to reconstructing history from match results
        if not history:
            print(f"DEBUG: No history in stats or profile, fetching matches for {player_id}...")
            results_url = f"https://app.utrsports.net/api/v1/player/{player_id}/results"
            try:
                res = requests.get(results_url, params={'top': 200}, headers=headers, cookies=auth_info.get('cookies'), timeout=15)
                if res.status_code == 200:
                    data = res.json()
                    events = data.get('events', [])
                    match_history = []
                    for event in events:
                        for draw in event.get('draws', []):
                            for result in draw.get('results', []):
                                players = result.get('players', {})
                                w = players.get('winner1', {})
                                l = players.get('loser1', {})
                                date_val = result.get('date') or result.get('resultDate') or event.get('startDate')
                                if date_val:
                                    rating = None
                                    if str(w.get('id')) == player_id:
                                        rating = w.get('myUtrSingles') or w.get('singlesUtr')
                                    elif str(l.get('id')) == player_id:
                                        rating = l.get('myUtrSingles') or l.get('singlesUtr')
                                    
                                    if rating:
                                        match_history.append({'date': date_val, 'rating': rating})
                    
                    if match_history:
                        # Inject CURRENT precise rating
                        if precise_rating:
                            match_history.append({'date': datetime.now().strftime("%Y-%m-%dT00:00:00"), 'rating': precise_rating})
                        history = match_history
            except: pass
        
        if history:
            history.sort(key=lambda x: x.get('date', ''), reverse=True)
            seen_dates = set()
            count = 0
            for entry in history:
                date_val = entry.get('date')
                rating = entry.get('rating')
                if date_val and rating:
                    formatted_date = date_val[:10]
                    if formatted_date in seen_dates:
                        continue
                    seen_dates.add(formatted_date)
                    
                    # PRIORITY: Inject precise rating for recent entries
                    if precise_rating and count == 0:
                        try:
                            entry_dt = datetime.strptime(formatted_date, "%Y-%m-%d")
                            if (datetime.now() - entry_dt).days < 30:
                                rating = precise_rating
                                print(f"DEBUG: Using precise rating {rating} for recent entry {formatted_date}")
                        except: pass

                    tennis_db.save_history(conn, {
                        'player_id': player_id,
                        'date': formatted_date,
                        'rating': rating,
                        'type': 'singles' 
                    })
                    count += 1
            conn.commit()
            return count
            
    except Exception as e:
        print(f"Error for {name}: {e}")
    finally:
        conn.close()
    return 0

def import_utr_history(country='CAN', player_name=None, max_workers=10):
    auth_info = login()
    tennis_db.init_db()
    conn = tennis_db.get_connection()
    conn.row_factory = tennis_db.sqlite3.Row
    c = conn.cursor()
    
    if player_name:
        print(f"\nSearching for player: {player_name}...")
        query = "SELECT player_id, name FROM players WHERE name LIKE ?"
        c.execute(query, (f"%{player_name}%",))
    else:
        print(f"\nFetching players from DB (Country={country})...")
        query = "SELECT player_id, name FROM players WHERE country = ?"
        c.execute(query, (country,))
        
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        if player_name:
            print(f"No player found matching '{player_name}'.")
        else:
            print(f"No players found for country {country}.")
        return

    print(f"Found {len(rows)} players. Fetching UTR history...")
    
    total_records = 0
    processed_players = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Map futures
        futures = {executor.submit(fetch_and_save_history, auth_info, dict(row)): row['name'] for row in rows}
        
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                count = future.result()
                total_records += count
                processed_players += 1
                
                # Update status
                if len(rows) > 1:
                    sys.stdout.write(f"\rProcessed {processed_players}/{len(rows)} players (Total Records: {total_records})...")
                    sys.stdout.flush()
                else:
                    print(f"   Done: {name} (+{count} records)")
            except Exception as exc:
                print(f"\n{name} generated an exception: {exc}")

    if len(rows) > 1:
        print(f"\n\nImport Complete! Saved {total_records} historical UTR points for {len(rows)} players.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Import UTR History for Existing Players')
    parser.add_argument('--country', default='CAN', help='Country (default: CAN)')
    parser.add_argument('--name', help='Filter by player name (e.g. "Shapovalov")')
    parser.add_argument('--workers', type=int, default=10, help='Workers (default: 10)')
    
    args = parser.parse_args()
    
    import_utr_history(args.country, args.name, args.workers)
