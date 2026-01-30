import csv
import json
import requests
import time
import datetime as dt
import concurrent.futures
import threading
import re
import os
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
from config import UTR_CONFIG
CONFIG = UTR_CONFIG
INPUT_FILE = 'd1_players_from_web.csv'
OUTPUT_FILE = 'd1_players_enriched_v2.csv'

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
        resp = requests.post("https://app.utrsports.net/api/v1/auth/login", json=CONFIG)
        if resp.status_code == 200:
            data = resp.json()
            token = data.get('jwt') or data.get('token')
            return {'token': token, 'cookies': resp.cookies}
    except Exception as e:
        print(f"Login failed: {e}")
    return None

def search_player(auth, name, college_hint=None):
    headers = {'Authorization': f"Bearer {auth['token']}"}
    # Search for verified players specifically
    params = {'query': name, 'top': 5, 'utrType': 'verified'}
    try:
        resp = requests.get("https://app.utrsports.net/api/v2/search/players", params=params, headers=headers)
        hits = resp.json().get('hits', [])
        
        if hits:
            # Prefer match with college
            if college_hint:
                for h in hits:
                    src = h.get('source', h)
                    pc = src.get('playerCollege', {})
                    if pc and pc.get('name'):
                        if college_hint.lower() in pc['name'].lower() or \
                           pc['name'].lower() in college_hint.lower():
                            return src
            return hits[0].get('source', hits[0])
    except:
        pass
    return None

def get_player_full_data(auth, player_id):
    headers = {'Authorization': f"Bearer {auth['token']}"}
    data = {}
    
    # 1. Profile
    try:
        p_resp = requests.get(f"https://app.utrsports.net/api/v1/player/{player_id}", headers=headers)
        p_data = p_resp.json()
        data['profile'] = p_data
    except:
        return None

    # 2. Stats (Peak, Min, History)
    try:
        s_resp = requests.get(f"https://app.utrsports.net/api/v1/player/{player_id}/stats", 
                             params={'type': 'singles', 'resultType': 'verified', 'Months': 12}, 
                             headers=headers)
        data['stats'] = s_resp.json()
    except:
        data['stats'] = {}

    # 3. Results (Matches)
    try:
        r_resp = requests.get(f"https://app.utrsports.net/api/v1/player/{player_id}/results", 
                             params={'top': 100}, headers=headers)
        data['results'] = r_resp.json()
    except:
        data['results'] = {}
        
    return data

def calculate_metrics(player_id, full_data):
    metrics = {
        'winLoss': '-', 'winPercent': '0%', 'upsetRatio': '0/0 (0%)',
        'avgOppUtr': '-', 'threeSetRecord': '0-0', 'recentForm': '-',
        'tournamentCount': 0, 'higherRatedWinPct': '0/0 (0%)',
        'tiebreakRecord': '0-0', 'comebackWins': 0,
        'peakUtr': '-', 'minRating': '-'
    }
    
    profile = full_data.get('profile', {})
    stats = full_data.get('stats', {})
    results = full_data.get('results', {})
    
    one_year_ago = dt.datetime.now() - dt.timedelta(days=365)
    
    # Peak/Min from Stats
    if stats.get('maxRating'): metrics['peakUtr'] = stats['maxRating']
    if stats.get('minRating'): metrics['minRating'] = stats['minRating']
    
    # Process Matches
    events = results.get('events', [])
    all_wins, all_losses = 0, 0
    upsets, opponent_utrs = 0, []
    three_set_wins, three_set_losses = 0, 0
    higher_rated_wins, higher_rated_matches = 0, 0
    tiebreak_wins, tiebreak_losses = 0, 0
    comeback_wins = 0
    all_matches = []
    event_ids = set()
    
    player_id_str = str(player_id)
    
    for event in events:
        event_ids.add(event.get('id'))
        for draw in event.get('draws', []):
            for res in draw.get('results', []):
                players = res.get('players', {})
                winner = players.get('winner1', {})
                loser = players.get('loser1', {})
                score = res.get('score', {})
                
                is_win = str(winner.get('id')) == player_id_str
                is_loss = str(loser.get('id')) == player_id_str
                
                if not is_win and not is_loss: continue
                
                # Metrics logic similar to scraper_analyst.py
                sets = len(score) if score else 0
                is_three_set = sets >= 3
                
                my_utr = winner.get('singlesUtr') if is_win else loser.get('singlesUtr')
                opp_utr = loser.get('singlesUtr') if is_win else winner.get('singlesUtr')
                
                if opp_utr: opponent_utrs.append(opp_utr)
                
                if is_win:
                    all_wins += 1
                    if opp_utr and my_utr and opp_utr > my_utr:
                        upsets += 1
                        higher_rated_wins += 1
                        higher_rated_matches += 1
                    if is_three_set: three_set_wins += 1
                    
                    # Comeback
                    if score and '1' in score:
                        s1 = score['1']
                        if s1.get('winner', 0) < s1.get('loser', 0):
                            comeback_wins += 1
                else:
                    all_losses += 1
                    if opp_utr and my_utr and opp_utr > my_utr:
                        higher_rated_matches += 1
                    if is_three_set: three_set_losses += 1
                
                # Tiebreaks
                for sk, sd in (score or {}).items():
                    if sd and sd.get('tiebreak') is not None:
                        w_tb = sd.get('winnerTiebreak', 0) or 0
                        l_tb = sd.get('tiebreak', 0) or 0
                        if is_win:
                            if w_tb > l_tb: tiebreak_wins += 1
                            else: tiebreak_losses += 1
                        else:
                            if l_tb > w_tb: tiebreak_wins += 1
                            else: tiebreak_losses += 1
                
                all_matches.append((res.get('date'), is_win))

    # Aggregates
    total = all_wins + all_losses
    if total > 0:
        metrics['winLoss'] = f"{all_wins}W-{all_losses}L"
        metrics['winPercent'] = f"{(all_wins/total)*100:.1f}%"
        if all_wins > 0:
            metrics['upsetRatio'] = f"{upsets}/{all_wins} ({upsets/all_wins:.0%})"
        if opponent_utrs:
            metrics['avgOppUtr'] = f"{sum(opponent_utrs)/len(opponent_utrs):.2f}"
            
    ts_total = three_set_wins + three_set_losses
    if ts_total > 0:
        metrics['threeSetRecord'] = f"{three_set_wins}W-{three_set_losses}L ({(three_set_wins/ts_total)*100:.0f}%)"
        
    if higher_rated_matches > 0:
        metrics['higherRatedWinPct'] = f"{higher_rated_wins}/{higher_rated_matches} ({(higher_rated_wins/higher_rated_matches)*100:.0f}%)"
        
    tb_total = tiebreak_wins + tiebreak_losses
    if tb_total > 0:
        metrics['tiebreakRecord'] = f"{tiebreak_wins}W-{tiebreak_losses}L ({(tiebreak_wins/tb_total)*100:.0f}%)"
        
    metrics['comebackWins'] = comeback_wins
    metrics['tournamentCount'] = len(event_ids)
    
    # Recent Form
    form_matches = sorted([m for m in all_matches if m[0]], key=lambda x: x[0], reverse=True)[:10]
    if form_matches:
        fw = sum(1 for m in form_matches if m[1])
        metrics['recentForm'] = f"{fw}W-{len(form_matches)-fw}L"
        
    return metrics

def process_row_wrapper(args):
    auth, row, writer, fout = args
    school, name = row[0], row[1]
    
    print(f"Searching {name} ({school})...")
    hit = search_player(auth, name, school)
    if not hit:
        print(f"  Not found: {name}")
        return

    pid = hit.get('id')
    full_data = get_player_full_data(auth, pid)
    if not full_data: return
    
    calc = calculate_metrics(pid, full_data)
    profile = full_data['profile']
    stats = full_data['stats']
    
    # Year Delta Calculation
    year_delta = ''
    history = stats.get('extendedRatingProfile', {}).get('history', []) or stats.get('ratingHistory', [])
    if history:
        # Find rating closest to 1 year ago
        one_year_ago = dt.datetime.now() - dt.timedelta(days=365)
        closest_rating = None
        min_diff = float('inf')
        for entry in history:
            try:
                edate = dt.datetime.fromisoformat(entry['date'].replace('Z', '+00:00')).replace(tzinfo=None)
                diff = abs((edate - one_year_ago).total_seconds())
                if diff < min_diff:
                    min_diff = diff
                    closest_rating = entry.get('rating')
            except: pass
        if closest_rating and min_diff < (30 * 24 * 3600): # Within a month
            curr = profile.get('singlesUtr') or hit.get('singlesUtr') or 0
            if curr and closest_rating:
                year_delta = f"{curr - closest_rating:+.2f}"

    # Construct Output
    out_row = {
        'Rank': '',
        'Name': profile.get('displayName') or f"{profile.get('firstName')} {profile.get('lastName')}",
        'College': school,
        'Division': 'D1',
        'Singles UTR': profile.get('singlesUtr') or hit.get('singlesUtr'),
        'Doubles UTR': profile.get('doublesUtr') or hit.get('doublesUtr'),
        'Peak UTR': calc['peakUtr'],
        'Min Rating': calc['minRating'],
        '3-Month Trend': stats.get('threeMonthRatingChangeDetails', {}).get('ratingDifference', ''),
        '1-Year Delta': year_delta,
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
        'Age': profile.get('age', ''),
        'Country': profile.get('nationality', ''),
        'Location': profile.get('location', {}).get('display', ''),
        'Pro Rank': '-', # Could be fetched from thirdPartyRankings
        'Profile URL': f"https://app.utrsports.net/profiles/{pid}"
    }
    
    # Pro Rank check
    rankings = profile.get('thirdPartyRankings', [])
    if rankings:
        out_row['Pro Rank'] = f"{rankings[0].get('source')} #{rankings[0].get('rank')}"

    with csv_lock:
        writer.writerow(out_row)
        fout.flush()
    print(f"  Processed: {name} | UTR: {out_row['Singles UTR']}")

def main():
    auth = login()
    if not auth: return
    
    rows = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as fin:
        reader = csv.reader(fin)
        next(reader, None) # Skip header
        rows = list(reader)
        
    print(f"Starting enrichment for {len(rows)} players...")
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as fout:
        writer = csv.DictWriter(fout, fieldnames=COLUMNS)
        writer.writeheader()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            args_list = [(auth, row, writer, fout) for row in rows]
            list(executor.map(process_row_wrapper, args_list))

if __name__ == "__main__":
    main()
