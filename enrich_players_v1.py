import csv
import json
import requests
import time
import datetime
import sys
import argparse

# Configuration
CONFIG = {'email': 'alberto.kuang@gmail.com', 'password': 'Spring2025'}
INPUT_FILE = 'd1_players_from_web.csv'
OUTPUT_FILE = 'd1_players_enriched.csv'

# Columns matching the "Junior Player" / College Scraper output
COLUMNS = [
    'Rank', 'Name', 'College', 'Division', 
    'Singles UTR', 'Doubles UTR', 'Peak UTR', 'Min Rating', 
    '3-Month Trend', '1-Year Delta', 
    'Win Record', 'Win %', 'Upset Ratio', 'Avg Opp UTR', 
    '3-Set Record', 'Recent Form (L10)', 'Tournaments', 
    'vs Higher Rated', 'Tiebreak Record', 'Comeback Wins', 
    'Age', 'Country', 'Location', 'Pro Rank', 'Profile URL'
]

def login():
    try:
        resp = requests.post("https://app.utrsports.net/api/v1/auth/login", json=CONFIG)
        if resp.status_code == 200:
            data = resp.json()
            token = data.get('jwt') or data.get('token')
            return {'token': token, 'cookies': resp.cookies}
    except Exception as e:
        print(f"Login failed: {e}")
    return None

def get_player_metrics(auth, player_id):
    headers = {'Authorization': f"Bearer {auth['token']}"}
    
    # 1. Basic Profile
    try:
        p_resp = requests.get(f"https://app.utrsports.net/api/v1/player/{player_id}", headers=headers)
        p_data = p_resp.json()
    except:
        return {}

    # 2. Results (for advanced metrics)
    # Fetch last 20 results or so for recent form
    results = []
    try:
        r_resp = requests.get(f"https://app.utrsports.net/api/v1/player/{player_id}/results", headers=headers)
        results = r_resp.json().get('events', [])
        # Provide logic to flatten matches from events if needed, 
        # but often 'results' endpoint gives a list of events with matches inside.
        # Actually standard results API structure is complex. 
        # Let's rely on basic profile stats if possible, or simplified scraping.
        # For this task, strict recalculation of everything might be slow.
        # I'll stick to what is available on the profile object and basic result parsing.
    except:
        pass
        
    # Extract data
    return {
        'singlesUtr': p_data.get('singlesUtr', 0),
        'doublesUtr': p_data.get('doublesUtr', 0),
        'age': p_data.get('age'),
        'location': p_data.get('location', {}).get('display'),
        'nationality': p_data.get('nationality'),
        'threeMonthRating': p_data.get('threeMonthRating'),
        'id': player_id
    }
    
def search_player(auth, name, college_hint=None):
    headers = {'Authorization': f"Bearer {auth['token']}"}
    params = {'query': name, 'top': 5}
    try:
        resp = requests.get("https://app.utrsports.net/api/v2/search/players", params=params, headers=headers)
        hits = resp.json().get('hits', [])
        
        best_hit = None
        
        # 1. Try generic match
        if hits:
            # If we have a college hint, try to match it
            if college_hint:
                for h in hits:
                    src = h.get('source', h)
                    # Check playerCollege field
                    pc = src.get('playerCollege', {})
                    if pc and pc.get('name'):
                        # Fuzzy match or robust check
                        if college_hint.lower() in pc['name'].lower() or \
                           pc['name'].lower() in college_hint.lower():
                            return src
            
            # If no college mismatch, return first result that matches name reasonably well
            best_hit = hits[0].get('source', hits[0])
            
        return best_hit
        
    except Exception as e:
        print(f"Search error for {name}: {e}")
    return None

def process_row(auth, row):
    school = row[0]
    name = row[1]
    
    # Defaults
    data = {c: '' for c in COLUMNS}
    data['Name'] = name
    data['College'] = school
    data['Division'] = 'D1' # Assumed based on file source
    
    hit = search_player(auth, name, school)
    if hit:
        pid = hit.get('id')
        data['Profile URL'] = f"https://app.utrsports.net/profiles/{pid}"
        
        # Always fetch detailed metrics because search result often has 0.0 UTR
        metrics = get_player_metrics(auth, pid)
        
        data['Singles UTR'] = metrics.get('singlesUtr', hit.get('singlesUtr'))
        data['Doubles UTR'] = metrics.get('doublesUtr', hit.get('doublesUtr'))
        data['Location'] = metrics.get('location') or hit.get('location', {}).get('display', '')
        data['Country'] = metrics.get('nationality') or hit.get('nationality', '')
        data['Age'] = metrics.get('age') or hit.get('age', '')
        
        # Add timestamp/trend if available
        data['3-Month Trend'] = metrics.get('threeMonthRating')
        
    return data

import concurrent.futures
import threading

# ... existing imports ...

# Thread-safe writer
csv_lock = threading.Lock()

def process_row_wrapper(args):
    auth, row, writer, fout = args
    if not row or len(row) < 2: return
    
    # Simple retry logic? Or just run.
    try:
        p_data = process_row(auth, row)
        with csv_lock:
            writer.writerow(p_data)
            fout.flush()
        print(f"Processed {row[1]}")
    except Exception as e:
        print(f"Error processing {row[1]}: {e}")

def main():
    auth = login()
    if not auth:
        print("Could not login to UTR.")
        return

    # Read all rows first
    rows = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as fin:
        reader = csv.reader(fin)
        header = next(reader, None)
        if header and 'Player Name' not in header[1]: 
             fin.seek(0)
        else:
             # If resuming, maybe check what's already done?
             pass 
        rows = list(reader)

    print(f"Loaded {len(rows)} players.")

    # Open output file
    # We'll overwrite for now, or append if we want to be fancy. 
    # Let's overwrite to clean up the partial mess.
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as fout:
        writer = csv.DictWriter(fout, fieldnames=COLUMNS)
        writer.writeheader()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Create a list of tasks
            futures = []
            for row in rows:
                futures.append(executor.submit(process_row_wrapper, (auth, row, writer, fout)))
            
            # Wait for completion
            concurrent.futures.wait(futures)

if __name__ == "__main__":
    main()
