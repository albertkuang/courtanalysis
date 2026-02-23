
import argparse
import time
import requests
import sys
import concurrent.futures
import tennis_db
from config import UTR_CONFIG
from datetime import datetime

# Configuration
CONFIG = UTR_CONFIG
LOGIN_URL = "https://app.utrsports.net/api/v1/auth/login"

def login():
    """Authenticate with UTR API"""
    print("Logging in to UTR...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(LOGIN_URL, json={
            "email": CONFIG['email'],
            "password": CONFIG['password']
        }, headers=headers, timeout=30)
        
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

def refresh_player_history(auth_info, player, overwrite=False):
    """
    Fetch and save UTR history for a single player.
    """
    player_id = str(player['player_id'])
    name = player['name']
    
    headers = {'Authorization': f"Bearer {auth_info['token']}"}
    
    # Track stats
    stats = {'processed': 0, 'added': 0, 'errors': 0, 'details': []}
    
    try:
        # Fetch UTR History
        stats_url = f"https://app.utrsports.net/api/v1/player/{player_id}/stats"
        
        # Try a few combinations because UTR API is restrictive
        # 1. verified/12, 2. myutr/12, 3. verified/6
        success = False
        s_data = None
        
        for rt in ['verified', 'myutr']:
            if success: break
            for m in [12, 6]:
                params = {'type': 'singles', 'resultType': rt, 'Months': m}
                res = requests.get(stats_url, params=params, headers=headers, cookies=auth_info.get('cookies'), timeout=15)
                if res.status_code == 200:
                    s_data = res.json()
                    success = True
                    break
                elif res.status_code == 400:
                    continue # Try next combo
        
        if success and s_data:
            history = (s_data.get('extendedRatingProfile') or {}).get('history') or s_data.get('ratingHistory', [])
            
            conn = tennis_db.get_connection()
            
            for entry in history:
                try:
                    stats['processed'] += 1
                    rating = entry.get('rating')
                    date_val = entry.get('date')
                    if not date_val: continue
                    date_str = date_val.replace('Z', '') 
                    
                    history_data = {
                        'player_id': player_id,
                        'date': date_str,
                        'rating': rating,
                        'type': 'singles'
                    }
                    
                    inserted = tennis_db.save_history(conn, history_data, overwrite=overwrite)
                    if inserted > 0:
                        stats['added'] += 1
                        stats['details'].append(f"  + {date_str[:10]}: {rating}")
                        
                except Exception as he:
                    stats['errors'] += 1
            
            # Doubles History
            params['type'] = 'doubles'
            d_res = requests.get(stats_url, params=params, headers=headers, cookies=auth_info.get('cookies'), timeout=15)
            if d_res.status_code == 200:
                d_data = d_res.json()
                d_history = (d_data.get('extendedRatingProfile') or {}).get('history') or d_data.get('ratingHistory', [])
                for entry in d_history:
                    try:
                        stats['processed'] += 1
                        rating = entry.get('rating')
                        date_val = entry.get('date')
                        if not date_val: continue
                        date_str = date_val.replace('Z', '')
                        
                        history_data = {
                            'player_id': player_id,
                            'date': date_str,
                            'rating': rating,
                            'type': 'doubles'
                        }
                        
                        inserted = tennis_db.save_history(conn, history_data, overwrite=overwrite)
                        if inserted > 0:
                            stats['added'] += 1
                            stats['details'].append(f"  + {date_str[:10]} (D): {rating}")
                    except: pass
            
            conn.commit()
            conn.close()
            return stats

        else:
             # Last status code if we have one or 400
             code = 400 
             print(f"Error fetching history for {name}: {code}")
             return None
        
    except Exception as e:
        print(f"Error processing history for {name}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Refresh Player UTR History (Delta Update)')
    parser.add_argument('--country', default='ALL', help='Country code or ALL (default: ALL)')
    parser.add_argument('--days', type=int, default=1, help='Update players older than X days (default: 1)')
    parser.add_argument('--limit', type=int, default=100, help='Max players to process (default: 100)')
    parser.add_argument('--min-utr', type=float, default=5.0, help='Min UTR to update (default: 5.0)')
    parser.add_argument('--max-utr', type=float, default=17.0, help='Max UTR to update (default: 17.0)')
    parser.add_argument('--force', action='store_true', help='Update all matching players regardless of timestamp')
    parser.add_argument('--workers', type=int, default=10, help='Concurrent workers (default: 10)')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing history (Default: Add Only)')
    
    args = parser.parse_args()
    
    print(f"\nRefreshing UTR History Data")
    print(f"   Country: {args.country}")
    print(f"   Age Limit: > {args.days} days")
    print(f"   UTR Range: {args.min_utr} - {args.max_utr}")
    print(f"   Mode: {'Overwrite' if args.overwrite else 'Add Only'}")
    print(f"   Batch Limit: {args.limit}")
    
    # 1. Login
    auth_info = login()
    
    # 2. Get Candidates
    tennis_db.init_db()
    conn = tennis_db.get_connection()
    try:
        candidates = tennis_db.get_players_for_refresh(
            conn, 
            country=args.country, 
            days_old=args.days, 
            limit=args.limit,
            min_utr=args.min_utr,
            max_utr=args.max_utr,
            force_update=args.force
        )
    finally:
        conn.close()
        
    if not candidates:
        print("   No players need history refresh matching criteria.")
        return

    print(f"   Found {len(candidates)} players to scan for history.")
    
    # 3. Process
    processed_count = 0
    total_added = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(refresh_player_history, auth_info, p, args.overwrite): p for p in candidates}
        
        for future in concurrent.futures.as_completed(futures):
            player = futures[future]
            processed_count += 1
            
            try:
                result = future.result()
                if result:
                    added = result['added']
                    total_added += added
                    processed = result['processed']
                    mode_str = "Overwritten" if args.overwrite and added > 0 else "Added"
                    
                    if added > 0:
                        print(f"   [{processed_count}/{len(candidates)}] {player['name']:<25} | {mode_str} {added}/{processed} records")
                        # Show first 3 details + count if more
                        details = result.get('details', [])
                        for i, detail in enumerate(details):
                            if i < 3: print(f"   {detail}")
                        if len(details) > 3:
                            print(f"   ... and {len(details)-3} more")
                    else:
                        print(f"   [{processed_count}/{len(candidates)}] {player['name']:<25} | No new history records")
                else:
                    print(f"   [{processed_count}/{len(candidates)}] Failed to refresh history for {player['name']}")
                    
            except Exception as e:
                print(f"   Error processing {player['name']}: {e}")

    print(f"\nUTR History Refresh Complete. Added {total_added} records across {processed_count} players.")

if __name__ == "__main__":
    main()
