"""
Populate Historical Juniors (2015-2022)
Scrapes match history for players aged 18-25 to capture their junior years.
"""

import requests
import sys
import argparse
import time
import datetime as dt
import tennis_db
from config import UTR_CONFIG

CONFIG = UTR_CONFIG
LOGIN_URL = "https://app.utrsports.net/api/v1/auth/login"
SEARCH_URL = "https://app.utrsports.net/api/v2/search/players"

# Major tennis countries contributing most top juniors
TARGET_COUNTRIES = [
    'USA', 'ESP', 'FRA', 'GBR', 'AUS', 'ITA', 'SRB', 'CZE', 'RUS', 'JPN',
    'ARG', 'CAN', 'BRA', 'DEU', 'POL', 'CHN'
]

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

def search_players(auth_info, country, gender, age_min=18, age_max=25, top=100):
    params = {
        'top': top,
        'skip': 0,
        'gender': gender,
        'utrMin': 8, # Focus on decent level players who likely played high level juniors
        'utrMax': 16.5,
        'utrType': 'verified',
        'nationality': country,
        'minAge': age_min,
        'maxAge': age_max,
        'query': ''
    }
    
    headers = {}
    if auth_info.get('token'):
        headers['Authorization'] = f"Bearer {auth_info['token']}"
    
    try:
        response = requests.get(SEARCH_URL, params=params, headers=headers, cookies=auth_info.get('cookies'))
        if response.status_code == 200:
            data = response.json()
            return data.get('hits', []) or data.get('players', [])
    except Exception as e:
        print(f"Search failed: {e}")
    return []

def fetch_player_history(auth_info, player_summary, conn):
    player_id = player_summary.get('id')
    name = player_summary.get('displayName')
    print(f"  Processing {name} ({player_id})...")
    
    headers = {}
    if auth_info.get('token'):
        headers['Authorization'] = f"Bearer {auth_info['token']}"
        
    results_url = f"https://app.utrsports.net/api/v1/player/{player_id}/results"
    
    skip = 0
    batch_size = 100
    done = False
    matches_saved = 0
    
    updated_player = {
        'player_id': str(player_id),
        'name': name,
        'country': player_summary.get('nationality'),
        'gender': player_summary.get('gender')
    }
    tennis_db.save_player(conn, updated_player)
    
    while not done:
        params = {'top': batch_size, 'skip': skip}
        
        try:
            resp = requests.get(results_url, params=params, headers=headers, cookies=auth_info.get('cookies'))
            if resp.status_code != 200:
                print(f"    Failed to fetch batch (skip={skip}): {resp.status_code}")
                break
                
            data = resp.json()
            events = data.get('events', [])
            
            if not events:
                done = True
                continue
                
            for event in events:
                # Check date - we want 2015 onwards
                date_str = event.get('startDate') or event.get('endDate')
                if not date_str:
                    continue
                    
                year = int(date_str[:4])
                if year < 2015:
                    # We can stop if we hit data older than 2015 as results are usually desc
                    done = True 
                    break
                
                # Filter for Junior tournaments if possible, but honestly saving all history is better
                # But to save time/space, we prefer ITF / Junior events
                # event_name = event.get('name', '')
                # if 'Junior' not in event_name and 'ITF' not in event_name and 'Grade' not in event_name:
                #    continue

                for draw in event.get('draws', []):
                    for result in draw.get('results', []):
                        winner = result.get('players', {}).get('winner1', {})
                        loser = result.get('players', {}).get('loser1', {})
                        score = result.get('score', {})
                        
                        match_id = result.get('id')
                        
                        # Format score
                        score_str = ""
                        if score:
                            for i in range(1, 6):
                                s = score.get(str(i))
                                if s:
                                    score_str += f"{s.get('winner')}-{s.get('loser')} "
                        
                        match_data = {
                            'match_id': match_id,
                            'date': date_str,
                            'winner_id': str(winner.get('id')),
                            'loser_id': str(loser.get('id')),
                            'score': score_str.strip(),
                            'tournament': event.get('name'),
                            'round': draw.get('name'),
                            'source': 'UTR_HISTORICAL',
                            'winner_utr': winner.get('singlesUtr'),
                            'loser_utr': loser.get('singlesUtr'),
                            'processed_player_id': str(player_id)
                        }
                        
                        try:
                            tennis_db.save_match(conn, match_data)
                            matches_saved += 1
                        except Exception as e:
                            # print(f"    Error saving match: {e}")
                            pass
            
            skip += batch_size
            time.sleep(0.1) # Fast but polite
            
        except Exception as e:
            print(f"    Error getting results: {e}")
            done = True
            
    print(f"    Saved {matches_saved} matches.")
    return matches_saved

def main():
    print("==========================================")
    print("   POPULATE HISTORICAL JUNIORS (2015+)")
    print("==========================================")
    
    auth_info = login()
    tennis_db.init_db()
    conn = tennis_db.get_connection()
    
    total_saved = 0
    
    for country in TARGET_COUNTRIES:
        print(f"\nSearching {country} for players aged 18-25...")
        
        # Gender Loop
        for gender in ['M', 'F']:
            print(f"  Gender: {gender}")
            # Search for top 50 players in this demographic per country
            players = search_players(auth_info, country, gender, top=50)
            
            print(f"  Found {len(players)} players.")
            
            for p in players:
                count = fetch_player_history(auth_info, p, conn)
                total_saved += count
                conn.commit()
                
    conn.close()
    print("\n==========================================")
    print(f"Done. Total matches saved: {total_saved}")
    print("==========================================")

if __name__ == "__main__":
    main()
