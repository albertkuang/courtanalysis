
import requests
import sys
import argparse
import time
import tennis_db
from config import UTR_CONFIG
from datetime import datetime
import json

# Configuration
CONFIG = UTR_CONFIG
LOGIN_URL = "https://app.utrsports.net/api/v1/auth/login"

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

def fetch_and_save_matches(auth_info, player_id, conn):
    """
    Fetches all matches for a player and saves them to the 'matches' table.
    """
    headers = {'Authorization': f"Bearer {auth_info['token']}"}
    results_url = f"https://app.utrsports.net/api/v1/player/{player_id}/results"
    
    skip = 0
    batch_size = 100
    done = False
    total_saved = 0
    
    while not done:
        params = {'top': batch_size, 'skip': skip}
        
        try:
            # Retry logic
            resp = None
            for attempt in range(3):
                try:
                    resp = requests.get(results_url, params=params, headers=headers, cookies=auth_info.get('cookies'))
                    if resp.status_code == 200:
                        break
                    elif resp.status_code == 429:
                        time.sleep(2 * (attempt + 1))
                except:
                    time.sleep(1)
            
            if not resp or resp.status_code != 200:
                print(f"  Failed batch at skip={skip}")
                break
                
            data = resp.json()
            events = data.get('events', [])
            
            if not events:
                done = True
                break
                
            for event in events:
                event_name = event.get('name')
                event_date_str = event.get('startDate') or event.get('endDate')
                event_date_obj = None
                if event_date_str:
                    try:
                        event_date_obj = datetime.fromisoformat(event_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                    except: pass

                for draw in event.get('draws', []):
                    draw_name = draw.get('name')
                    
                    for result in draw.get('results', []):
                        # Determine date
                        res_date_str = result.get('date') or result.get('resultDate')
                        res_date_obj = None
                        if res_date_str:
                            try:
                                res_date_obj = datetime.fromisoformat(res_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                            except: pass
                        
                        final_date = res_date_obj or event_date_obj
                        final_date_iso = final_date.isoformat() if final_date else None
                        
                        winner = result.get('players', {}).get('winner1', {})
                        loser = result.get('players', {}).get('loser1', {})
                        score = result.get('score', {})
                        
                        # Only process if valid players
                        if not winner.get('id') or not loser.get('id'):
                            continue
                            
                        # Format score string
                        score_str = ""
                        for i in range(1, 6):
                            s_set = score.get(str(i))
                            if s_set:
                                score_str += f"{s_set.get('winner')}-{s_set.get('loser')} "
                            else: break
                        score_str = score_str.strip()
                        
                        # Construct Match Object
                        match_data = {
                            'match_id': result.get('id'),
                            'date': final_date_iso,
                            'winner_id': str(winner.get('id')),
                            'winner_name': winner.get('displayName') or f"{winner.get('firstName')} {winner.get('lastName')}", # Helper for auto-create
                            'loser_id': str(loser.get('id')),
                            'loser_name': loser.get('displayName') or f"{loser.get('firstName')} {loser.get('lastName')}", # Helper for auto-create
                            'score': score_str,
                            'tournament': event_name,
                            'round': draw_name,
                            'source': 'UTR',
                            'winner_utr': winner.get('singlesUtr'),
                            'loser_utr': loser.get('singlesUtr'),
                            'processed_player_id': player_id
                        }
                        
                        tennis_db.save_match(conn, match_data)
                        total_saved += 1
            
            skip += batch_size
            # Safety limit to avoid infinite loops if API is weird
            if skip > 5000: 
                done = True
                
        except Exception as e:
            print(f"Error fetching matches: {e}")
            break
            
    return total_saved

def import_matches(country='CAN', category=None, min_utr=0, max_workers=10):
    auth_info = login()
    tennis_db.init_db()
    conn = tennis_db.get_connection()
    c = conn.cursor()
    
    print(f"\nScanning local DB for players from {country} with UTR >= {min_utr}...")
    
    # Base query
    query = "SELECT player_id, name, age_group, utr_singles FROM players WHERE country = ?"
    params = [country]
    
    if min_utr > 0:
        query += " AND utr_singles >= ?"
        params.append(min_utr)
    
    c.execute(query, params)
    all_players = c.fetchall()
    
    # Filter in Python because SQLite regex/logic is limited
    players_to_process = []
    
    if category:
        print(f"Filtering for category: {category}")
        for pid, name, ag, utr in all_players:
            if not ag:
                # If no age group, assuming included unless filtered strictly? 
                # Actually, let's include if category logic is ambiguous or just skip?
                # For safety, if category is strictly requested, we might need AG. 
                # But UTR scraper might not always get AG.
                # Let's simple check if we can determine.
                pass 
                
            is_adult = False
            if ag and (ag.startswith('19') or ag[0] in ['2','3','4','5','6','7','8','9'] or 
                ag.startswith('>') or ag.lower().startswith('over') or ag.lower() == 'adult'):
                is_adult = True
            
            # If AG is missing, we can't be sure, but usually high UTR without AG is pro/adult. 
            # Let's keep existing logic but be mindful.
            # Existing logic skipped if `not ag`.
            if not ag:
                 # Fallback: if min_utr is high (>10), treat as adult/relevant?
                 # For now, replicate existing behavior roughly but fix the unpacking
                 continue

            if category == 'adult' and is_adult:
                players_to_process.append((pid, name))
            elif category == 'junior' and not is_adult:
                players_to_process.append((pid, name))
    else:
        players_to_process = [(p[0], p[1]) for p in all_players]
    
    if not players_to_process:
        print(f"No players found in DB for {country} (Category: {category}, UTR >= {min_utr}).")
        conn.close()
        return

    print(f"Found {len(players_to_process)} players. Fetching match history with {max_workers} workers...")
    
    import concurrent.futures
    import queue
    import threading
    
    # Queue for matches to save (producer-consumer pattern)
    match_queue = queue.Queue()
    stop_signal = threading.Event()
    total_saved = [0]
    
    # Single DB writer thread (avoids locking)
    def db_writer():
        writer_conn = tennis_db.get_connection()
        while not stop_signal.is_set() or not match_queue.empty():
            try:
                match_data = match_queue.get(timeout=0.5)
                tennis_db.save_match(writer_conn, match_data)
                total_saved[0] += 1
                if total_saved[0] % 500 == 0:
                    writer_conn.commit()
                match_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                pass  # Silently skip errors
        writer_conn.commit()
        writer_conn.close()
    
    writer_thread = threading.Thread(target=db_writer, daemon=True)
    writer_thread.start()
    
    # Modified fetch function - returns matches to queue instead of saving directly
    def fetch_matches_to_queue(player_id):
        headers = {'Authorization': f"Bearer {auth_info['token']}"}
        results_url = f"https://app.utrsports.net/api/v1/player/{player_id}/results"
        
        skip = 0
        batch_size = 100
        count = 0
        
        while True:
            params_req = {'top': batch_size, 'skip': skip}
            try:
                resp = requests.get(results_url, params=params_req, headers=headers, cookies=auth_info.get('cookies'), timeout=30)
                if resp.status_code != 200:
                    break
                    
                data = resp.json()
                events = data.get('events', [])
                
                if not events:
                    break
                    
                for event in events:
                    event_name = event.get('name')
                    event_date_str = event.get('startDate') or event.get('endDate')
                    event_date_obj = None
                    if event_date_str:
                        try:
                            event_date_obj = datetime.fromisoformat(event_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                        except: pass

                    for draw in event.get('draws', []):
                        draw_name = draw.get('name')
                        
                        for result in draw.get('results', []):
                            res_date_str = result.get('date') or result.get('resultDate')
                            res_date_obj = None
                            if res_date_str:
                                try:
                                    res_date_obj = datetime.fromisoformat(res_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                                except: pass
                            
                            final_date = res_date_obj or event_date_obj
                            final_date_iso = final_date.isoformat() if final_date else None
                            
                            winner = result.get('players', {}).get('winner1', {})
                            loser = result.get('players', {}).get('loser1', {})
                            score = result.get('score', {})
                            
                            if not winner.get('id') or not loser.get('id'):
                                continue
                                
                            score_str = ""
                            for i in range(1, 6):
                                s_set = score.get(str(i))
                                if s_set:
                                    score_str += f"{s_set.get('winner')}-{s_set.get('loser')} "
                                else: break
                            
                            match_data = {
                                'match_id': result.get('id'),
                                'date': final_date_iso,
                                'winner_id': str(winner.get('id')),
                                'winner_name': winner.get('displayName') or f"{winner.get('firstName') or ''} {winner.get('lastName') or ''}".strip(),
                                'loser_id': str(loser.get('id')),
                                'loser_name': loser.get('displayName') or f"{loser.get('firstName') or ''} {loser.get('lastName') or ''}".strip(),
                                'score': score_str.strip(),
                                'tournament': event_name,
                                'round': draw_name,
                                'source': 'UTR',
                                'winner_utr': winner.get('singlesUtr'),
                                'loser_utr': loser.get('singlesUtr'),
                                'processed_player_id': player_id
                            }
                            match_queue.put(match_data)
                            count += 1
                
                skip += batch_size
                if skip > 5000:
                    break
                    
            except Exception as e:
                break
        
        return count
    
    processed = [0]
    total_players = len(players_to_process)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_matches_to_queue, p[0]): p for p in players_to_process}
        
        for future in concurrent.futures.as_completed(futures):
            processed[0] += 1
            if processed[0] % 10 == 0 or processed[0] == total_players:
                sys.stdout.write(f"\rFetched: {processed[0]}/{total_players} players | Queue: {match_queue.qsize()} | Saved: {total_saved[0]}")
                sys.stdout.flush()
    
    # Wait for queue to drain
    print(f"\nWaiting for DB writes to complete...")
    match_queue.join()
    stop_signal.set()
    writer_thread.join(timeout=10)
    
    conn.close()
    print(f"\nImport Complete! Total matches saved: {total_saved[0]}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Import Match History for Existing Players')
    parser.add_argument('--country', default='CAN', help='Country Code filter for local DB (default: CAN)')
    parser.add_argument('--category', default=None, help='Category filter: junior or adult (default: None = all)')
    parser.add_argument('--min-utr', type=float, default=0, help='Minimum UTR to filter by (default: 0)')
    parser.add_argument('--workers', type=int, default=10, help='Number of concurrent workers (default: 10)')
    
    args = parser.parse_args()
    
    import_matches(args.country, args.category, args.min_utr, args.workers)
