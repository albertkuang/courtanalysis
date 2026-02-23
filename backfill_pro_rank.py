import requests
import sqlite3
import json
import time
import os
import sys

# Load config
try:
    import config
    UTR_CONFIG = config.UTR_CONFIG
except ImportError:
    print("Error: config.py not found or missing UTR_CONFIG.")
    sys.exit(1)

def get_auth_token():
    """Login and get API token."""
    url = "https://app.utrsports.net/api/v1/auth/login"
    payload = {
        "email": UTR_CONFIG['email'],
        "password": UTR_CONFIG['password']
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        token = data.get('jwt') or data.get('token')
        if not token:
             # Try cookies
             token = response.cookies.get('jwt')
        return token
    except Exception as e:
        print(f"Login failed: {e}")
        return None

def backfill_ranks():
    # 1. Connect DB
    conn = sqlite3.connect('tennis_data.db')
    c = conn.cursor()
    
    # 2. Get high UTR players (likely to have rank)
    c.execute("SELECT player_id, name FROM players WHERE pro_rank IS NULL AND utr_singles > 10 ORDER BY utr_singles DESC")
    players = c.fetchall()
    
    print(f"Found {len(players)} players with >10 UTR and missing pro_rank.")
    
    # 3. Login
    token = get_auth_token()
    if not token:
        return
        
    headers = {
        'Authorization': f"Bearer {token}",
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    count = 0
    updated = 0
    
    for pid, name in players:
        count += 1
        print(f"[{count}/{len(players)}] Checking {name} ({pid})...")
        
        try:
            # Fetch Profile V2
            r = requests.get(f"https://app.utrsports.net/api/v2/player/{pid}", headers=headers)
            
            if r.status_code == 200:
                data = r.json()
                
                # DEBUG: Dump first one to see structure
                if count == 1:
                    with open('player_profile_debug.json', 'w') as f:
                        json.dump(data, f, indent=2)
                    print("Saved debug JSON to player_profile_debug.json")

                rankings = data.get('thirdPartyRankings', [])
                for item in rankings:
                    source = item.get('source')
                    rtype = item.get('type')
                    rank_val = item.get('rank')
                    
                    if source in ['ATP', 'WTA'] and rtype == 'Singles':
                         rank_str = f"{source} #{rank_val}"
                         break
                    if source == 'ITF' and rtype == 'Singles' and not rank_str:
                         rank_str = f"ITF #{rank_val}"
                
                if rank_str:
                    print(f"  -> FOUND RANK: {rank_str}")
                    c.execute("UPDATE players SET pro_rank = ? WHERE player_id = ?", (rank_str, pid))
                    conn.commit()
                    updated += 1
                else:
                    print("  -> No rank found.")
                    
            elif r.status_code == 429: # Rate limit
                print("Rate limit hit. Sleeping 60s...")
                time.sleep(60)
            else:
                print(f"  Error {r.status_code}")
                
        except Exception as e:
            print(f"  Exception: {e}")
            
        time.sleep(0.5) # Faster pace
        
        # Process all (remove limit or set high)
        if count >= 3000: break # Safety cap

    print(f"Updated {updated} players.")
    conn.close()

if __name__ == '__main__':
    backfill_ranks()
