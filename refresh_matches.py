
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

def refresh_player_matches(auth_info, player, overwrite=False):
    """
    Fetch and save matches for a single player.
    """
    player_id = str(player['player_id'])
    name = player['name']
    
    headers = {'Authorization': f"Bearer {auth_info['token']}"}
    
    # Track stats
    stats = {'processed': 0, 'added': 0, 'errors': 0, 'details': []}
    
    try:
        # Fetch Match Results
        # We fetch top 100 matches. Adjust 'top' if needed for deeper history.
        results_url = f"https://app.utrsports.net/api/v1/player/{player_id}/results"
        r_params = {'top': 100} 
        r_res = requests.get(results_url, params=r_params, headers=headers, cookies=auth_info.get('cookies'), timeout=15)
        
        if r_res.status_code == 200:
            r_data = r_res.json()
            events = r_data.get('events', [])
            
            conn = tennis_db.get_connection()
            
            for event in events:
                tournament_name = event.get('name')
                for draw in event.get('draws', []):
                    round_name = draw.get('name') # e.g. "Main Draw"
                    for result in draw.get('results', []):
                        try:
                            stats['processed'] += 1
                            match_id = str(result.get('id'))
                            date_str = result.get('date') # ISO format
                            
                            winner = result.get('players', {}).get('winner1', {})
                            loser = result.get('players', {}).get('loser1', {})
                            score = result.get('score', {})
                            
                            # Construct score string
                            score_parts = []
                            for k in sorted(score.keys()):
                                s = score[k]
                                if s:
                                    score_parts.append(f"{s.get('winner')}-{s.get('loser')}")
                                    if s.get('tiebreak'):
                                        score_parts[-1] += f"({s.get('tiebreak')})"
                            score_str = ", ".join(score_parts)
                            
                            w_name = f"{winner.get('firstName')} {winner.get('lastName')}"
                            l_name = f"{loser.get('firstName')} {loser.get('lastName')}"
                            
                            match_data = {
                                'match_id': match_id,
                                'date': date_str,
                                'winner_id': winner.get('id'),
                                'loser_id': loser.get('id'),
                                'winner_name': w_name,
                                'loser_name': l_name,
                                'winner_utr': winner.get('usi'),
                                'loser_utr': loser.get('usi'),
                                'score': score_str,
                                'tournament': tournament_name,
                                'round': round_name,
                                'source': 'UTR_API_REFRESH',
                                'processed_player_id': player_id
                            }
                            
                            inserted = tennis_db.save_match(conn, match_data, overwrite=overwrite)
                            if inserted > 0:
                                stats['added'] += 1
                                stats['details'].append(f"  + {date_str[:10]}: {w_name} vs {l_name} ({score_str})")
                                
                        except Exception as me:
                            stats['errors'] += 1
            
            conn.commit()
            conn.close()
            return stats

        else:
             print(f"Error fetching matches for {name}: {r_res.status_code}")
             return None
        
    except Exception as e:
        print(f"Error processing matches for {name}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Refresh Player Matches (Delta Update)')
    parser.add_argument('--country', default='ALL', help='Country code or ALL (default: ALL)')
    parser.add_argument('--days', type=int, default=1, help='Update players older than X days (default: 1)')
    parser.add_argument('--limit', type=int, default=100, help='Max players to process (default: 100)')
    parser.add_argument('--min-utr', type=float, default=5.0, help='Min UTR to update (default: 5.0)')
    parser.add_argument('--max-utr', type=float, default=17.0, help='Max UTR to update (default: 17.0)')
    parser.add_argument('--force', action='store_true', help='Update all matching players regardless of timestamp')
    parser.add_argument('--workers', type=int, default=10, help='Concurrent workers (default: 10)')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing matches (Default: Add Only)')
    
    args = parser.parse_args()
    
    print(f"\nRefreshing Match Data")
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
        print("   No players need match refresh matching criteria.")
        return

    print(f"   Found {len(candidates)} players to scan for new matches.")
    
    # 3. Process
    processed_count = 0
    total_added = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(refresh_player_matches, auth_info, p, args.overwrite): p for p in candidates}
        
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
                        print(f"   [{processed_count}/{len(candidates)}] {player['name']:<25} | {mode_str} {added}/{processed} matches")
                        for detail in result.get('details', []):
                            print(f"   {detail}")
                    else:
                        print(f"   [{processed_count}/{len(candidates)}] {player['name']:<25} | No new matches found")
                else:
                    print(f"   [{processed_count}/{len(candidates)}] Failed to refresh matches for {player['name']}")
                    
            except Exception as e:
                print(f"   Error processing {player['name']}: {e}")

    print(f"\nMatch Refresh Complete. Added {total_added} matches across {processed_count} players.")

if __name__ == "__main__":
    main()
