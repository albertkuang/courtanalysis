
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

def refresh_player_metrics(auth_info, player):
    """
    Fetch updated metrics for a single player.
    """
    player_id = player['player_id']
    name = player['name']
    
    # We prepare a dict with ONLY the fields we want to update
    # The save_player function uses COALESCE, so missing fields won't overwrite existing data with NULL
    update_data = {
        'player_id': player_id,
        # We include name just in case it changed/corrected, though rarely needed
        'name': name 
    }
    
    headers = {'Authorization': f"Bearer {auth_info['token']}"}
    
    try:
        # 1. Fetch V2 Profile (Current UTR, Pro Rank)
        v2_url = f"https://app.utrsports.net/api/v2/player/{player_id}"
        v2_res = requests.get(v2_url, headers=headers, cookies=auth_info.get('cookies'), timeout=10)
        
        if v2_res.status_code == 200:
            v2 = v2_res.json()
            
            # Update UTRs
            update_data['utr_singles'] = v2.get('singlesUtr')
            update_data['utr_doubles'] = v2.get('doublesUtr')
            
            # Update Pro Rank if available (only if valid value)
            if v2.get('proRankings'):
                s_rank = v2.get('proRankings', {}).get('singles')
                if s_rank:
                    update_data['pro_rank'] = s_rank
                
            # Update Age if available (keeps it fresh)
            if v2.get('age'):
                update_data['age'] = v2.get('age')
                
        # 2. Fetch Match Results (for calculated metrics)
        # We need recent matches to calculate "Form" metrics
        results_url = f"https://app.utrsports.net/api/v1/player/{player_id}/results"
        r_params = {'top': 50} 
        r_res = requests.get(results_url, params=r_params, headers=headers, cookies=auth_info.get('cookies'), timeout=15)
        
        if r_res.status_code == 200:
            r_data = r_res.json()
            
            comeback_wins = 0
            tiebreak_wins = 0
            tiebreak_losses = 0
            three_set_wins = 0
            three_set_losses = 0
            
            for event in r_data.get('events', []):
                for draw in event.get('draws', []):
                    for result in draw.get('results', []):
                        winner = result.get('players', {}).get('winner1', {})
                        loser = result.get('players', {}).get('loser1', {})
                        score = result.get('score', {})
                        
                        is_winner = str(winner.get('id')) == player_id
                        is_loser = str(loser.get('id')) == player_id
                        
                        if not is_winner and not is_loser: continue
                        
                        # Tiebreaks
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

                        # 3-Setters
                        num_sets = len(score) if score else 0
                        if num_sets >= 3:
                            if is_winner: three_set_wins += 1
                            else: three_set_losses += 1
                            
                        # Comebacks (Winner lost 1st Set)
                        if is_winner and score and '1' in score:
                            first_set = score['1']
                            if first_set:
                                w_score = first_set.get('winner') or 0
                                l_score = first_set.get('loser') or 0
                                if w_score < l_score:
                                    comeback_wins += 1
            
            update_data['comeback_wins'] = comeback_wins
            update_data['tiebreak_wins'] = tiebreak_wins
            update_data['tiebreak_losses'] = tiebreak_losses
            update_data['three_set_wins'] = three_set_wins
            update_data['three_set_losses'] = three_set_losses

        return update_data
        
    except Exception as e:
        print(f"Error refreshing {name}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Refresh Player Stats & UTRs')
    parser.add_argument('--country', default='ALL', help='Country code or ALL (default: ALL)')
    parser.add_argument('--days', type=int, default=1, help='Update players older than X days (default: 1)')
    parser.add_argument('--limit', type=int, default=100, help='Max players to process (default: 100)')
    parser.add_argument('--workers', type=int, default=10, help='Concurrent workers (default: 10)')
    parser.add_argument('--min-utr', type=float, default=5.0, help='Min UTR to update (default: 5.0)')
    parser.add_argument('--max-utr', type=float, default=17.0, help='Max UTR to update (default: 17.0)')
    parser.add_argument('--force', action='store_true', help='Update all matching players regardless of timestamp')
    
    args = parser.parse_args()
    
    print(f"\nRefreshing Player Data")
    print(f"   Country: {args.country}")
    print(f"   Age Limit: > {args.days} days (Ignored if --force)" if args.force else f"   Age Limit: > {args.days} days")
    print(f"   UTR Range: {args.min_utr} - {args.max_utr}")
    print(f"   Force Update: {args.force}")
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
        print("   No players need refreshing matching criteria.")
        return

    print(f"   Found {len(candidates)} players to refresh.")
    
    # 3. Process
    processed_count = 0
    updated_count = 0
    
    conn = tennis_db.get_connection()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(refresh_player_metrics, auth_info, p): p for p in candidates}
        
        for future in concurrent.futures.as_completed(futures):
            player = futures[future]
            processed_count += 1
            
            try:
                result = future.result()
                if result:
                    # Save update
                    tennis_db.save_player(conn, result)
                    updated_count += 1
                    
                    # Calculate Diffs
                    changes = []
                    
                    # UTR Singles
                    old_utr = player.get('utr_singles') or 0
                    new_utr = result.get('utr_singles') or 0
                    if abs(new_utr - old_utr) > 0.01:
                        changes.append(f"UTR: {old_utr:.2f}->{new_utr:.2f}")
                        
                    # UTR Doubles
                    old_dutr = player.get('utr_doubles') or 0
                    new_dutr = result.get('utr_doubles') or 0
                    if abs(new_dutr - old_dutr) > 0.01:
                        changes.append(f"D-UTR: {old_dutr:.2f}->{new_dutr:.2f}")

                    # Pro Rank
                    old_rank = player.get('pro_rank')
                    new_rank = result.get('pro_rank')
                    if str(old_rank) != str(new_rank):
                         changes.append(f"Rank: {old_rank}->{new_rank}")
                         
                    # Metrics (Comebacks etc)
                    # Just check one as proxy for "Stats Updated"
                    old_cb = player.get('comeback_wins') or 0
                    new_cb = result.get('comeback_wins') or 0
                    if new_cb != old_cb:
                        changes.append(f"Comebacks: {old_cb}->{new_cb}")

                    change_str = ", ".join(changes) if changes else "No Change"
                    print(f"   [{processed_count}/{len(candidates)}] {player['name']:<25} | {change_str}")
                else:
                    print(f"   [{processed_count}/{len(candidates)}] Failed to refresh {player['name']}")
                    
            except Exception as e:
                print(f"   Error processing {player['name']}: {e}")
                
            # Commit every 10 updates
            if updated_count % 10 == 0:
                conn.commit()

    conn.commit()
    conn.close()
    print(f"\nRefresh Complete. Updated {updated_count} players.")

if __name__ == "__main__":
    main()
