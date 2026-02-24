
import requests
import sys
import datetime as dt

# Configuration
DEFAULT_PLAYER = "Angelina Chacko" 
CONFIG = {
    'email': 'alberto.kuang@gmail.com',
    'password': 'Spring2025'
}
LOGIN_URL = "https://app.utrsports.net/api/v1/auth/login"
SEARCH_URL = "https://app.utrsports.net/api/v2/search/players"

def login():
    """Authenticate with UTR API."""
    try:
        response = requests.post(LOGIN_URL, json=CONFIG)
        if response.status_code != 200:
            print(f"Error: Login failed ({response.status_code})")
            sys.exit(1)
        data = response.json()
        token = data.get('jwt') or data.get('token')
        if not token:
            for cookie in response.cookies:
                if cookie.name == 'jwt':
                    token = cookie.value
                    break
        return {'token': token, 'cookies': response.cookies}
    except Exception as e:
        print(f"Error during login: {e}")
        sys.exit(1)

def safe_date_parse(date_str):
    if not date_str: return None
    try:
        return dt.datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
    except:
        return None

def fetch_and_display_history(player_name, save_csv=False, save_db=False, skip_existing=False):
    # 1. Login
    auth = login()
    headers = {'Authorization': f"Bearer {auth['token']}"}

    # 2. Search Player
    s_params = {'query': player_name, 'top': 1}
    try:
        resp = requests.get(SEARCH_URL, params=s_params, headers=headers, cookies=auth.get('cookies'))
        hits = resp.json().get('hits', [])
    except Exception as e:
        print(f"Error searching player: {e}")
        return

    if not hits:
        print(f"Player '{player_name}' not found.")
        return

    player_source = hits[0].get('source')
    player_id = player_source['id']
    display_name = player_source.get('displayName')
    
    # 3. Check DB Count vs UTR Total (Optimization)
    if skip_existing:
        import tennis_db
        try:
            conn = tennis_db.get_connection()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM matches WHERE winner_id = ? OR loser_id = ?", (str(player_id), str(player_id)))
            db_count = c.fetchone()[0]
            conn.close()
            
            # Initial API probe for total
            results_url = f"https://app.utrsports.net/api/v1/player/{player_id}/results"
            probe_res = requests.get(results_url, params={'top': 1, 'skip': 0}, headers=headers, cookies=auth.get('cookies'))
            if probe_res.status_code == 200:
                utr_total = probe_res.json().get('total', 0)
                if utr_total > 0 and db_count >= utr_total:
                    print(f"Skipping {display_name}: DB has {db_count} matches, UTR has {utr_total}.")
                    return
                elif utr_total > 0:
                    print(f"Syncing {display_name}: DB={db_count}, UTR={utr_total}...")
        except Exception as e:
            print(f"Warning: Failed to check existing DB counts: {e}")

    # 4. Fetch Matches
    results_url = f"https://app.utrsports.net/api/v1/player/{player_id}/results"
    
    matches_data_full = [] # Store full data for DB save
    matches = []
    seen_synthetic = set()
    skip = 0
    batch_size = 100
    
    while True:
        r_params = {'top': batch_size, 'skip': skip}
        try:
            res = requests.get(results_url, params=r_params, headers=headers, cookies=auth.get('cookies'))
            if res.status_code != 200: break
            
            data = res.json()
            events = data.get('events', [])
            
            if not events: break
            
            new_matches_in_batch = 0
            
            for event in events:
                e_date_str = event.get('startDate') or event.get('endDate')
                e_date = safe_date_parse(e_date_str)
                event_name = event.get('name', 'Unknown Tournament')
                
                for draw in event.get('draws', []):
                    draw_name = draw.get('name', 'Main Draw')
                    for result in draw.get('results', []):
                        
                        # Filter Doubles
                        players = result.get('players', {})
                        if players.get('winner2') or players.get('loser2'):
                            continue

                        # Dates
                        r_date_str = result.get('date') or result.get('resultDate')
                        r_date = safe_date_parse(r_date_str)
                        final_date = r_date or e_date or dt.datetime(1970, 1, 1)
                        date_str = final_date.strftime('%Y-%m-%d')

                        # Players & Score
                        w_p = players.get('winner1', {})
                        l_p = players.get('loser1', {})
                        
                        w_id = w_p.get('id')
                        l_id = l_p.get('id')
                        
                        def get_name(p_obj):
                            dn = p_obj.get('displayName')
                            if dn: return dn
                            fn = p_obj.get('firstName', '')
                            ln = p_obj.get('lastName', '')
                            if fn or ln: return f"{fn} {ln}".strip()
                            return "Unknown"

                        winner_name = get_name(w_p)
                        loser_name = get_name(l_p)
                        
                        score = result.get('score', {})
                        score_str = " ".join([f"{v.get('winner')}-{v.get('loser')}" for k, v in score.items()])
                        
                        # Determine Result
                        if str(w_id) == str(player_id):
                            result_lbl = "Win"
                            opponent = loser_name
                        else:
                            result_lbl = "Loss"
                            opponent = winner_name

                        # Synthetic Deduplication
                        if w_id and l_id:
                            ids_sorted = sorted([str(w_id), str(l_id)])
                            syn_key = f"{date_str}|{ids_sorted[0]}|{ids_sorted[1]}|{score_str}"
                        else:
                            syn_key = f"{date_str}|{score_str}"

                        if syn_key in seen_synthetic:
                            continue
                        
                        seen_synthetic.add(syn_key)
                        
                        # Match Object for Display
                        match_obj = {
                            'date': final_date,
                            'date_str': date_str,
                            'result': result_lbl,
                            'opponent': opponent,
                            'score': score_str,
                            'event': event_name
                        }
                        matches.append(match_obj)
                        
                        # Full Data for DB
                        if save_db:
                            db_match = {
                                'match_id': str(result.get('id')),
                                'date': final_date.isoformat(),
                                'winner_id': str(w_id),
                                'loser_id': str(l_id),
                                'winner_name': winner_name,
                                'loser_name': loser_name,
                                'winner_utr': w_p.get('singlesUtr'),
                                'loser_utr': l_p.get('singlesUtr'),
                                'score': score_str,
                                'tournament': event_name,
                                'round': draw_name,
                                'source': 'utr_api_diagnose',
                                'processed_player_id': str(player_id)
                            }
                            matches_data_full.append(db_match)
                            
                        new_matches_in_batch += 1

            if new_matches_in_batch == 0:
                break # Infinite loop protection

            skip += batch_size
            # if skip > 5000: break # Safety limit removed by request
            
        except Exception as e:
            break

    # Sort Descending
    matches.sort(key=lambda x: x['date'], reverse=True)

    # Output to Console
    print(f"Match History for {display_name}: {len(matches)} matches found")
    print("-" * 120)
    print(f"{'Date':<12} | {'Result':<6} | {'Opponent':<25} | {'Score':<15} | {'Tournament'}")
    print("-" * 120)
    
    for m in matches:
        opp = (m['opponent'][:23] + '..') if len(m['opponent']) > 23 else m['opponent']
        evt = (m['event'][:45] + '..') if len(m['event']) > 45 else m['event']
        print(f"{m['date_str']:<12} | {m['result']:<6} | {opp:<25} | {m['score']:<15} | {evt}")

    # CSV Export
    if save_csv:
        import csv
        filename = f"{display_name.replace(' ', '_')}_history.csv"
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Date', 'Result', 'Opponent', 'Score', 'Tournament'])
                for m in matches:
                    writer.writerow([m['date_str'], m['result'], m['opponent'], m['score'], m['event']])
            print(f"\nSuccessfully saved to {filename}")
        except Exception as e:
            print(f"\nError saving CSV: {e}")

    # DB Save
    if save_db:
        import tennis_db
        print(f"\nSaving {len(matches_data_full)} matches to database...")
        conn = tennis_db.get_connection()
        count = 0
        for m_data in matches_data_full:
            tennis_db.save_match(conn, m_data)
            count += 1
        conn.commit()
        conn.close()
        print(f"Saved {count} matches to DB.")

if __name__ == "__main__":
    import argparse
    import tennis_db

    parser = argparse.ArgumentParser(description="Fetch UTR match history.")
    parser.add_argument("player", nargs='?', help="Player name to search (Single Player Mode)")
    parser.add_argument("--csv", action="store_true", help="Save results to CSV file")
    parser.add_argument("--save-db", action="store_true", help="Save results to SQLite database")
    
    # Batch Mode Arguments
    parser.add_argument("--country", help="Filter players by country (e.g. USA, CAN)")
    parser.add_argument("--category", help="Filter by age group (e.g. Junior, Adult)")
    parser.add_argument("--gender", help="Filter by gender (M, F)")
    parser.add_argument("--skip-existing", action="store_true", help="Skip if DB matches UTR count")

    args = parser.parse_args()

    # Mode 1: Single Player
    if args.player:
        fetch_and_display_history(args.player, save_csv=args.csv, save_db=args.save_db, skip_existing=args.skip_existing)
    
    # Mode 2: Batch Processing
    elif args.country or args.category:
        print(f"--- Batch Mode: Country={args.country}, Category={args.category}, Gender={args.gender} ---")
        conn = tennis_db.get_connection()
        c = conn.cursor()
        
        query = "SELECT name FROM players WHERE 1=1"
        params = []
        
        if args.country:
            query += " AND country = ?"
            params.append(args.country)
        
        if args.category:
            cat_lower = args.category.lower()
            if cat_lower == 'adult':
                # Map 'Adult' to known adult age groups in DB
                adult_groups = ['19-22', '23-29', '30s', '40s', '50s', '60s', '>70']
                placeholders = ','.join(['?'] * len(adult_groups))
                query += f" AND age_group IN ({placeholders})"
                params.extend(adult_groups)
            elif cat_lower == 'junior':
                # Map 'Junior' to known junior age groups
                jr_groups = ['U10', 'U12', 'U13', 'U14', '14-18']
                placeholders = ','.join(['?'] * len(jr_groups))
                query += f" AND age_group IN ({placeholders})"
                params.extend(jr_groups)
            else:
                # Fallback to fuzzy match
                query += " AND age_group LIKE ?"
                params.append(f"%{args.category}%")
            
        if args.gender:
            query += " AND gender = ?"
            params.append(args.gender)
            
        # Order by UTR Descending
        query += " ORDER BY utr_singles DESC"
            
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        
        players_list = [r[0] for r in rows]
        print(f"Found {len(players_list)} players matching criteria.")
        
        for idx, p_name in enumerate(players_list, 1):
            print(f"\n[{idx}/{len(players_list)}] Processing Player: {p_name}")
            try:
                fetch_and_display_history(p_name, save_csv=args.csv, save_db=args.save_db, skip_existing=args.skip_existing)
            except Exception as e:
                print(f"Failed to process {p_name}: {e}")
                
    else:
        # Default behavior if nothing specified
        fetch_and_display_history(DEFAULT_PLAYER, save_csv=args.csv, save_db=args.save_db, skip_existing=args.skip_existing)
