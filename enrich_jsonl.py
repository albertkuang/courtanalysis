
import json
import requests
import sys
import os
import concurrent.futures
import argparse
from config import UTR_CONFIG

# API URLs
LOGIN_URL = "https://app.utrsports.net/api/v1/auth/login"

def login():
    try:
        resp = requests.post(LOGIN_URL, json={
            "email": UTR_CONFIG['email'],
            "password": UTR_CONFIG['password']
        }, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return {'token': data.get('jwt') or data.get('token'), 'cookies': resp.cookies}
        else:
            print(f"Login failed: {resp.status_code}")
    except Exception as e:
        print(f"Login error: {e}")
    return None

def get_headers(auth):
    return {
        'Authorization': f"Bearer {auth['token']}",
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
    }

def enrich_player(auth, player_data):
    pid = player_data.get('player_id')
    if not pid: return player_data
    
    url = f"https://app.utrsports.net/api/v2/player/{pid}"
    try:
        resp = requests.get(url, headers=get_headers(auth), timeout=10)
        if resp.status_code == 200:
            profile = resp.json()
            # Update fields missing from Search API
            player_data['age'] = profile.get('age')
            player_data['birth_date'] = profile.get('birthDate')
            player_data['location'] = profile.get('location', {}).get('display') or player_data.get('location')
            player_data['country'] = profile.get('nationality') or player_data.get('country')
            return player_data
        else:
            pass
    except Exception as e:
        pass
    
    return player_data

def main():
    parser = argparse.ArgumentParser(description='Enrich UTR players.jsonl with Age and Birthday info')
    parser.add_argument('--input', required=True, help='Path to players.jsonl')
    parser.add_argument('--output', help='Path to output file (defaults to input_enriched.jsonl)')
    parser.add_argument('--workers', type=int, default=15, help='Number of threads')
    args = parser.parse_args()

    input_file = args.input
    output_file = args.output or input_file.replace('.jsonl', '_enriched.jsonl')

    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        return

    auth = login()
    if not auth: return

    print(f"Reading players from {input_file}...")
    players = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    players.append(json.loads(line))
                except: continue

    print(f"Enriching {len(players)} players via Profile API...")
    
    enriched_count = 0
    with open(output_file, 'w', encoding='utf-8') as fout:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(enrich_player, auth, p): p for p in players}
            
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                try:
                    res = future.result()
                    if res.get('age') or res.get('birth_date'):
                        enriched_count += 1
                    fout.write(json.dumps(res, ensure_ascii=False) + '\n')
                    
                    if (i+1) % 25 == 0 or (i+1) == len(players):
                        sys.stdout.write(f"\rProcessed {i+1}/{len(players)} | Found Age for: {enriched_count}")
                        sys.stdout.flush()
                except Exception as e:
                    pass
                    
    print(f"\n\nDone! Saved to {output_file}")

if __name__ == "__main__":
    main()
