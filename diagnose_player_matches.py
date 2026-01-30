
import requests
import sqlite3
import datetime as dt
import tennis_db

# Config
PLAYER_NAME = "Kyle Kang"
CONFIG = {
    'email': 'alberto.kuang@gmail.com',
    'password': 'Spring2025'
}
LOGIN_URL = "https://app.utrsports.net/api/v1/auth/login"
SEARCH_URL = "https://app.utrsports.net/api/v2/search/players"

def login():
    print("Logging in...")
    response = requests.post(LOGIN_URL, json=CONFIG)
    if response.status_code != 200:
        raise Exception(f"Login failed: {response.status_code}")
    data = response.json()
    token = data.get('jwt') or data.get('token')
    if not token:
        for cookie in response.cookies:
            if cookie.name == 'jwt':
                token = cookie.value
                break
    return {'token': token, 'cookies': response.cookies}

def safe_date_parse(date_str):
    if not date_str: return None
    try:
        # Handle "2023-05-20T00:00:00Z"
        return dt.datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
    except:
        return None

def diagnose(player_name):
    # 1. Login
    auth = login()
    headers = {'Authorization': f"Bearer {auth['token']}"}

    # 2. Search
    print(f"Searching for {player_name}...")
    s_params = {'query': player_name, 'top': 1}
    resp = requests.get(SEARCH_URL, params=s_params, headers=headers, cookies=auth['cookies'])
    hits = resp.json().get('hits', [])
    if not hits:
        print("Player not found.")
        return

    player_source = hits[0].get('source')
    player_id = player_source['id']
    print(f"Found Player: {player_source['displayName']} (ID: {player_id})")

    # 3. Fetch Matches
    print("\n--- FETCHING MATCHES ---")
    results_url = f"https://app.utrsports.net/api/v1/player/{player_id}/results"
    
    one_year_ago = dt.datetime.now() - dt.timedelta(days=365)
    print(f"Date Cutoff: {one_year_ago}")

    skip = 0
    batch_size = 100
    done = False
    
    total_api_matches = 0
    accepted_matches = 0

    while not done:
        print(f"\nRequesting batch: skip={skip}...")
        r_params = {'top': batch_size, 'skip': skip}
        res = requests.get(results_url, params=r_params, headers=headers, cookies=auth['cookies'])
        
        data = res.json()
        events = data.get('events', [])
        
        if not events:
            print("No events in this batch. Done.")
            break
            
        print(f"Batch contains {len(events)} events.")
        
        batch_has_valid_dates = False

        for event in events:
            e_name = event.get('name')
            e_date_str = event.get('startDate') or event.get('endDate')
            e_date = safe_date_parse(e_date_str)
            
            print(f"  Event: {e_name} ({e_date_str})")
            
            if e_date and e_date < one_year_ago:
                print(f"    -> EVENT TOO OLD (Cutoff check)")
                # Continue investigating to see if logic is sound
            
            for draw in event.get('draws', []):
                for result in draw.get('results', []):
                    total_api_matches += 1
                    
                    r_id = result.get('id')
                    r_date_str = result.get('date') or result.get('resultDate')
                    r_date = safe_date_parse(r_date_str)
                    
                    # Determine actual date used
                    final_date = r_date or e_date
                    
                    is_excluded = False
                    reason = ""

                    if not final_date:
                        is_excluded = True
                        reason = "NO DATE"
                    elif final_date < one_year_ago:
                        is_excluded = True
                        reason = f"TOO OLD ({final_date})"
                    
                    status = "SKIP" if is_excluded else "KEEP"
                    if status == "KEEP":
                        accepted_matches += 1
                        batch_has_valid_dates = True
                    
                    score = result.get('score', {})
                    score_str = " ".join([f"{v.get('winner')}-{v.get('loser')}" for k, v in score.items()])
                    
                    print(f"    Match {r_id}: {r_date_str} | Score: {score_str} | [{status}] {reason}")

        # Check stopping condition logic from scraper_analyst.py
        # Logic: if found_old and len(events)>0...
        # Let's see if we are stopping too early
        
        last_event = events[-1]
        last_date_str = last_event.get('startDate') or last_event.get('endDate')
        last_date = safe_date_parse(last_date_str)
        
        if last_date and last_date < one_year_ago:
             print("!!! SCRAPER WOULD STOP HERE due to 'found_old' logical check !!!")
             # In original script:
             # if found_old: check last event. if last event is old, done = True
        
        skip += batch_size
        if skip >= 1000:
            done = True

    print("\n--- SUMMARY ---")
    print(f"Total Matches in API Stream: {total_api_matches}")
    print(f"Total Accepted (Within 1 Year): {accepted_matches}")

if __name__ == "__main__":
    diagnose(PLAYER_NAME)
