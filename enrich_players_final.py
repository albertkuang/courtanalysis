import csv
import json
import requests
import time
import datetime as dt
import concurrent.futures
import threading
import os
import urllib3
import tennis_db

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
CONFIG = {'email': 'alberto.kuang@gmail.com', 'password': 'Spring2025'}
INPUT_FILE = 'd1_players_from_web_women.csv'
OUTPUT_FILE = os.path.join('output', 'd1_players_enriched_final_women.csv')

COLUMNS = [
    'Rank', 'Name', 'College', 'Division', 
    'Singles UTR', 'Doubles UTR', 'Peak UTR', 'Min Rating', 
    '3-Month Trend', '1-Year Delta', 
    'Win Record', 'Win %', 'Upset Ratio', 'Avg Opp UTR', 
    '3-Set Record', 'Recent Form (L10)', 'Tournaments', 
    'vs Higher Rated', 'Tiebreak Record', 'Comeback Wins', 
    'Age', 'Country', 'Location', 'Pro Rank', 'Profile URL'
]

csv_lock = threading.Lock()

def login():
    try:
        resp = requests.post("https://app.utrsports.net/api/v1/auth/login", json=CONFIG, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {'token': data.get('jwt') or data.get('token'), 'cookies': resp.cookies}
    except Exception as e:
        print(f"Login failed: {e}")
    return None

def search_player(auth, name, college_hint=None):
    headers = {'Authorization': f"Bearer {auth['token']}"}
    # No utrType restriction to be safe
    params = {'query': name, 'top': 5}
    try:
        resp = requests.get("https://app.utrsports.net/api/v2/search/players", params=params, headers=headers, timeout=10)
        hits = resp.json().get('hits', [])
        if hits:
            if college_hint:
                for h in hits:
                    src = h.get('source', h)
                    pc = src.get('playerCollege', {})
                    if pc and pc.get('name') and college_hint.lower() in pc.get('name').lower():
                        return src
            return hits[0].get('source', hits[0])
    except: pass
    return None

def get_player_full_data(auth, player_id):
    headers = {'Authorization': f"Bearer {auth['token']}"}
    data = {'profile': {}, 'stats': {}, 'results': {}}
    
    # 1. Profile (V2 is key for decimals)
    try:
        p_resp = requests.get(f"https://app.utrsports.net/api/v2/player/{player_id}", headers=headers, timeout=10)
        if p_resp.status_code == 200: data['profile'] = p_resp.json()
    except: pass

    # 2. Stats
    try:
        s_resp = requests.get(f"https://app.utrsports.net/api/v1/player/{player_id}/stats", 
                             params={'type': 'singles', 'resultType': 'verified', 'Months': 12}, 
                             headers=headers, timeout=10)
        if s_resp.status_code == 200: 
            json_data = s_resp.json()
            if isinstance(json_data, dict):
                # Check for Federer fallback (subtitle containing 2019/2020)
                subtitle = json_data.get('subtitle', '')
                if "2019" in subtitle and "Federer" in str(json_data):
                     data['stats'] = {} # Ignore sample stats
                else:
                     data['stats'] = json_data
    except: pass

    # 3. Results
    try:
        r_resp = requests.get(f"https://app.utrsports.net/api/v1/player/{player_id}/results", 
                             params={'top': 100}, headers=headers, timeout=10)
        if r_resp.status_code == 200: data['results'] = r_resp.json()
    except: pass
    
    return data

def calculate_metrics(player_id, full_data):
    m = {
        'winLoss': '-', 'winPercent': '0%', 'upsetRatio': '0/0 (0%)',
        'avgOppUtr': '-', 'threeSetRecord': '0-0 (0%)', 'recentForm': '-',
        'tournamentCount': 0, 'higherRatedWinPct': '0/0 (0%)',
        'tiebreakRecord': '0-0 (0%)', 'comebackWins': 0,
        'peakUtr': '-', 'minRating': '-'
    }
    
    profile = full_data.get('profile') or {}
    stats = full_data.get('stats') or {}
    results = full_data.get('results') or {}
    
    # Peak/Min from Stats
    if stats:
        if stats.get('maxRating'): m['peakUtr'] = stats['maxRating']
        if stats.get('minRating'): m['minRating'] = stats['minRating']
    
    events = results.get('events', [])
    all_wins, all_losses = 0, 0
    upsets, opps = [], []
    ts_w, ts_l = 0, 0
    hr_w, hr_m = 0, 0
    tb_w, tb_l = 0, 0
    cb_w = 0
    matches = []
    e_ids = set()
    p_utrs = [] 
    
    pid_s = str(player_id)
    
    for event in events:
        e_ids.add(event.get('id'))
        for draw in event.get('draws', []):
            for res in draw.get('results', []):
                pl = res.get('players', {})
                w, l = pl.get('winner1', {}), pl.get('loser1', {})
                score = res.get('score', {})
                is_win = str(w.get('id')) == pid_s
                is_loss = str(l.get('id')) == pid_s
                if not is_win and not is_loss: continue
                
                # Use v2's high precision UTR if possible
                my_utr = w.get('singlesUtr') if is_win else l.get('singlesUtr')
                opp_utr = l.get('singlesUtr') if is_win else w.get('singlesUtr')
                
                if my_utr: p_utrs.append(my_utr)
                if opp_utr: opps.append(opp_utr)
                
                sets = len(score) if score else 0
                is_3 = sets >= 3
                
                if is_win:
                    all_wins += 1
                    if opp_utr and my_utr and opp_utr > my_utr:
                        upsets.append(opp_utr)
                        hr_w += 1
                        hr_m += 1
                    if is_3: ts_w += 1
                    if score and '1' in score:
                        s1 = score['1']
                        if s1.get('winner', 0) < s1.get('loser', 0): cb_w += 1
                else:
                    all_losses += 1
                    if opp_utr and my_utr and opp_utr > my_utr: hr_m += 1
                    if is_3: ts_l += 1
                
                for sk, sd in (score or {}).items():
                    if sd and sd.get('tiebreak') is not None:
                        w_tb, l_tb = sd.get('winnerTiebreak', 0) or 0, sd.get('tiebreak', 0) or 0
                        if is_win:
                            if w_tb > l_tb: tb_w += 1
                            else: tb_l += 1
                        else:
                            if l_tb > w_tb: tb_w += 1
                            else: tb_l += 1
                matches.append((res.get('date'), is_win))

    if m['peakUtr'] == '-' and p_utrs: m['peakUtr'] = f"{max(p_utrs):.2f}"
    if m['minRating'] == '-' and p_utrs: m['minRating'] = f"{min(p_utrs):.2f}"
    
    total = all_wins + all_losses
    if total > 0:
        m['winLoss'] = f"{all_wins}W-{all_losses}L"
        m['winPercent'] = f"{(all_wins/total)*100:.1f}%"
        if all_wins > 0: m['upsetRatio'] = f"{len(upsets)}/{all_wins} ({len(upsets)/all_wins:.0%})"
        if opps: m['avgOppUtr'] = f"{sum(opps)/len(opps):.2f}"
            
    ts_t = ts_w + ts_l
    if ts_t > 0: m['threeSetRecord'] = f"{ts_w}W-{ts_l}L ({(ts_w/ts_t)*100:.0f}%)"
    if hr_m > 0: m['higherRatedWinPct'] = f"{hr_w}/{hr_m} ({(hr_w/hr_m)*100:.0f}%)"
    tb_t = tb_w + tb_l
    if tb_t > 0: m['tiebreakRecord'] = f"{tb_w}W-{tb_l}L ({(tb_w/tb_t)*100:.0f}%)"
    m['comebackWins'] = cb_w
    m['tournamentCount'] = len(e_ids)
    
    form = sorted([ma for ma in matches if ma[0]], key=lambda x: x[0], reverse=True)[:10]
    if form:
        fw = sum(1 for ma in form if ma[1])
        m['recentForm'] = f"{fw}W-{len(form)-fw}L"
    return m

def save_data_to_sqlite(hit, full_data):
    """Save player and match data to SQLite."""
    try:
        conn = tennis_db.get_connection()
        
        # 1. Save Player
        p = full_data.get('profile') or {}
        pid = str(hit.get('id') or p.get('id'))
        
        player_data = {
            'player_id': pid,
            'name': p.get('displayName') or f"{p.get('firstName')} {p.get('lastName')}",
            'college': hit.get('school', {}).get('name') if isinstance(hit.get('school'), dict) else hit.get('school'), # simple extraction, might need refinement
            'country': p.get('nationality'),
            'gender': p.get('gender'),
            'utr_singles': p.get('myUtrSingles') or p.get('singlesUtr'),
            'utr_doubles': p.get('myUtrDoubles') or p.get('doublesUtr')
        }
        tennis_db.save_player(conn, player_data)
        
        tennis_db.save_player(conn, player_data)
        
        # 1.5 Save UTR History
        stats = full_data.get('stats') or {}
        history_list = stats.get('extendedRatingProfile', {}).get('history') or stats.get('ratingHistory', [])
        for h_item in history_list:
            if h_item.get('rating') and h_item.get('date'):
                tennis_db.save_history(conn, {
                    'player_id': pid,
                    'date': h_item.get('date'),
                    'rating': h_item.get('rating'),
                    'type': 'singles' # Assuming singles for now as stats call is type=singles
                })
        
        # 2. Save Matches
        results = full_data.get('results') or {}
        events = results.get('events', [])
        
        for event in events:
            event_name = event.get('name')
            for draw in event.get('draws', []):
                draw_name = draw.get('name')
                for res in draw.get('results', []):
                    match_id = res.get('id')
                    if not match_id: continue
                    
                    pl = res.get('players', {})
                    w = pl.get('winner1', {})
                    l = pl.get('loser1', {})
                    
                    score = res.get('score', {})
                    score_str = ""
                    # Construct simple score string
                    for i in range(1, 6):
                        s_set = score.get(str(i))
                        if s_set:
                            score_str += f"{s_set.get('winner')}-{s_set.get('loser')} "
                        else:
                            break
                    

                    # Tiebreak info could be added but keeping it simple for now
                    
                    # Save both players involved in the match
                    for p_obj in [w, l]:
                         if p_obj and p_obj.get('id'):
                             try:
                                 p_name = p_obj.get('displayName') or f"{p_obj.get('firstName', '')} {p_obj.get('lastName', '')}".strip()
                                 if p_name:
                                     tennis_db.save_player(conn, {
                                         'player_id': str(p_obj.get('id')),
                                         'name': p_name,
                                        'gender': p_obj.get('gender') or p.get('gender'),
                                         'utr_singles': p_obj.get('singlesUtr'),
                                         'utr_doubles': p_obj.get('doublesUtr')
                                     })
                             except: pass

                    match_data = {
                        'match_id': match_id,
                        'date': res.get('date'),
                        'winner_id': str(w.get('id')),
                        'loser_id': str(l.get('id')),
                        'score': score_str.strip(),
                        'tournament': event_name,
                        'round': draw_name,
                        'source': 'UTR',
                        'winner_utr': w.get('singlesUtr'),
                        'loser_utr': l.get('singlesUtr'),
                        'processed_player_id': pid
                    }
                    tennis_db.save_match(conn, match_data)
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error for {hit.get('name')}: {e}")

def process_row(auth, row, index):
    school, name = row[0], row[1]
    hit = search_player(auth, name, school)
    if not hit: return None
    
    pid = hit.get('id')
    full_data = get_player_full_data(auth, pid)
    
    # Save to SQLite
    save_data_to_sqlite(hit, full_data)
    
    calc = calculate_metrics(pid, full_data)
    
    p = full_data.get('profile') or {}
    s = full_data.get('stats') or {}
    
    # Year Delta
    delta = ''
    history = s.get('extendedRatingProfile', {}).get('history', []) or s.get('ratingHistory', []) if s else []
    if history:
        one_yr = dt.datetime.now() - dt.timedelta(days=365)
        closest_r, min_d = None, float('inf')
        for entry in history:
            try:
                edate = dt.datetime.fromisoformat(entry['date'].replace('Z', '+00:00')).replace(tzinfo=None)
                diff = abs((edate - one_yr).total_seconds())
                if diff < min_d: min_d = diff; closest_r = entry.get('rating')
            except: pass
        if closest_r and min_d < (45 * 24 * 3600):
            curr = p.get('myUtrSingles') or p.get('singlesUtr') or hit.get('myUtrSingles') or hit.get('singlesUtr') or 0
            if curr and closest_r: delta = f"{curr - closest_r:+.2f}"

    out = {
        'Rank': index,
        'Name': p.get('displayName') or f"{p.get('firstName')} {p.get('lastName')}" or name,
        'College': school,
        'Division': 'D1',
        'Singles UTR': p.get('myUtrSingles') or p.get('singlesUtr') or hit.get('myUtrSingles') or hit.get('singlesUtr') or 0,
        'Doubles UTR': p.get('myUtrDoubles') or p.get('doublesUtr') or hit.get('myUtrDoubles') or hit.get('doublesUtr') or '',
        'Peak UTR': calc['peakUtr'],
        'Min Rating': calc['minRating'],
        '3-Month Trend': s.get('threeMonthRatingChangeDetails', {}).get('ratingDifference', '') if s else '',
        '1-Year Delta': delta,
        'Win Record': calc['winLoss'],
        'Win %': calc['winPercent'],
        'Upset Ratio': calc['upsetRatio'],
        'Avg Opp UTR': calc['avgOppUtr'],
        '3-Set Record': calc['threeSetRecord'],
        'Recent Form (L10)': calc['recentForm'],
        'Tournaments': calc['tournamentCount'],
        'vs Higher Rated': calc['higherRatedWinPct'],
        'Tiebreak Record': calc['tiebreakRecord'],
        'Comeback Wins': calc['comebackWins'],
        'Age': p.get('age', ''),
        'Country': p.get('nationality', ''),
        'Location': p.get('location', {}).get('display', '') if p.get('location') else '',
        'Pro Rank': '-',
        'Profile URL': f"https://app.utrsports.net/profiles/{pid}"
    }
    
    # Format decimals
    for f in ['Singles UTR', 'Doubles UTR', 'Peak UTR', 'Min Rating']:
        if isinstance(out[f], (int, float)):
            out[f] = f"{out[f]:.2f}"
            
    rankings = p.get('thirdPartyRankings', [])
    if rankings: out['Pro Rank'] = f"{rankings[0].get('source')} #{rankings[0].get('rank')}"
    return out

def main():
    tennis_db.init_db() # Ensure DB exists
    auth = login()
    if not auth: return
    
    rows = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as fin:
        reader = csv.reader(fin)
        next(reader, None)
        rows = list(reader)
        
    print(f"Starting enrichment for {len(rows)} players...")
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as fout:
        writer = csv.DictWriter(fout, fieldnames=COLUMNS)
        writer.writeheader()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Wrap in list to block until all futures are created, but as_completed blocks until they finish
            futures = {executor.submit(process_row, auth, row, i+1): row for i, row in enumerate(rows)}
            count = 0
            for future in concurrent.futures.as_completed(futures):
                count += 1
                try:
                    res = future.result()
                    if res:
                        with csv_lock:
                            writer.writerow(res)
                            fout.flush()
                        if count % 20 == 0: print(f"Progress: {count}/{len(rows)}")
                except Exception as e:
                    print(f"Worker Error: {e}")

if __name__ == "__main__":
    main()
