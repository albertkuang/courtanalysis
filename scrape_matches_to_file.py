#!/usr/bin/env python3
"""
Phase 1: Scrape all data from UTR API to JSONL files.
Scrapes: Players, Match History, UTR History

This is fast because it only writes to disk - no database operations.

Usage:
    python scrape_matches_to_file.py --country CAN --category adult
    python scrape_matches_to_file.py --country CAN --category junior --output-dir ./data
    python scrape_matches_to_file.py --country USA --category adult --workers 15
"""

import requests
import sys
import argparse
import time
import json
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from config import UTR_CONFIG

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# API URLs
LOGIN_URL = "https://app.utrsports.net/api/v1/auth/login"
SEARCH_URL = "https://app.utrsports.net/api/v2/search/players"


def login():
    """Authenticate with UTR API."""
    print("🔐 Logging in to UTR...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(LOGIN_URL, json={
            "email": UTR_CONFIG['email'],
            "password": UTR_CONFIG['password']
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
        
        print("   ✓ Login successful!")
        return {'token': token, 'cookies': response.cookies}
    except Exception as e:
        print(f"   ✗ Login Error: {e}")
        sys.exit(1)


def get_headers(auth_info):
    return {
        'Authorization': f"Bearer {auth_info['token']}",
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
    }


# ============================================================================
# PHASE 1A: Scrape Players
# ============================================================================

def search_players_by_utr_band(auth_info, country, utr_min, utr_max, gender=None, age_tag=None):
    """Search for players in a UTR band."""
    headers = get_headers(auth_info)
    players = []
    skip = 0
    batch_size = 20  # API limit reduced to 20
    
    while True:
        params = {
            'top': batch_size,
            'skip': skip,
            'utrMin': utr_min,
            'utrMax': utr_max,
            'nationality': country
        }

        
        if gender:
            params['gender'] = gender
        
        # Use ageTags for junior/adult filtering (UTR's actual API parameter)
        if age_tag:
            params['ageTags'] = age_tag
        
        try:
            resp = requests.get(SEARCH_URL, params=params, headers=headers, 
                               cookies=auth_info.get('cookies'), timeout=30)
            
            if resp.status_code != 200:
                break
            
            data = resp.json()
            hits = data.get('hits', [])
            
            if not hits:
                break
            
            for hit in hits:
                source = hit.get('source', {})
                
                # Extract player data
                player = {
                    'player_id': str(source.get('id', '')),
                    'name': source.get('displayName') or f"{source.get('firstName', '')} {source.get('lastName', '')}".strip(),
                    'country': source.get('nationality') or country,
                    'gender': source.get('gender', ''),
                    'age': source.get('age'),
                    'birth_date': source.get('birthDate'),
                    'location': source.get('location', {}).get('display') if source.get('location') else None,
                    'utr_singles': source.get('singlesUtr'),
                    'utr_doubles': source.get('doublesUtr'),
                    'college': source.get('college') or source.get('school'),
                    'age_group': source.get('ageRange') or source.get('ageGroup'),
                    'pro_rank': source.get('proRankings', {}).get('singles') if source.get('proRankings') else None
                }
                
                # Normalize gender
                if player['gender'] == 'Male': player['gender'] = 'M'
                elif player['gender'] == 'Female': player['gender'] = 'F'
                
                if player['player_id']:
                    players.append(player)
            
            skip += batch_size
            
            # UTR API limits to 500 results per search (approx)
            if skip >= 500 or len(hits) < batch_size:
                break
                
        except Exception as e:
            break
    
    return players


def fetch_player_profile(auth_info, player_id):
    """Fetch full player profile to get age/birthdate."""
    headers = get_headers(auth_info)
    url = f"https://app.utrsports.net/api/v2/player/{player_id}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return {}


def scrape_all_players(auth_info, country, category, output_file=None, workers=20):
    """
    Scrape all players for a country/category using UTR band splitting + Alphabet partition.
    Writes incrementally to output_file if provided.
    """
    all_players = {}  # Dedupe in memory
    written_ids = set() # Track what's on disk
    
    file_lock = threading.Lock()
    player_lock = threading.Lock()
    
    # Age tag based on category
    if category == 'junior':
        age_tag = 'U18'
    else:
        age_tag = None
    
    genders = ['M', 'F']
    alphabet = list("abcdefghijklmnopqrstuvwxyz")
    
    print(f"\n   Searching UTR bands (Hybrid Recursive + Alphabet)...")

    def save_players_incremental(new_players):
        if not output_file: return
        with file_lock:
            with open(output_file, 'a', encoding='utf-8') as f:
                for p in new_players:
                    if p['player_id'] not in written_ids:
                        f.write(json.dumps(p, ensure_ascii=False) + '\n')
                        written_ids.add(p['player_id'])

    def fetch_band_with_query(min_u, max_u, gender, query=None):
        """Helper to fetch a specific band, optionally with a query char."""
        batch_size = 20  # API limit
        params = {
            'top': batch_size,
            'skip': 0,
            'utrMin': min_u,
            'utrMax': max_u,
            'nationality': country,
            'gender': gender
        }
        if age_tag: params['ageTags'] = age_tag
        if query: params['query'] = query
        
        fetched = []
        while True:
            try:
                # Retry wrapper
                r = None
                for attempt in range(3):
                    try:
                        r = requests.get(SEARCH_URL, params=params, headers=get_headers(auth_info), 
                                         cookies=auth_info.get('cookies'), timeout=20)
                        if r.status_code == 429:
                            time.sleep(2 * (attempt + 1)); continue
                        break
                    except: time.sleep(1)
                
                if not r or r.status_code != 200: break
                
                hits = r.json().get('hits', [])
                if not hits: break
                
                for hit in hits:
                    source = hit.get('source', {})
                    # Basic extraction (minimal)
                    pid = str(source.get('id', ''))
                    if not pid: continue
                    
                    # Adult filter: Only keep specific age groups
                    if category == 'adult' and age_tag is None:
                        ag = source.get('ageRange') or source.get('ageGroup') or ''
                        # Allowed groups: 19-22, 23-29, 30s
                        # Note: we might also want to include explicit ages if available?
                        # For now, stick to the user request.
                        
                        allowed_groups = ['19-22', '23-29', '30s']
                        if ag not in allowed_groups:
                            continue
                    
                    p = {
                        'player_id': pid,
                        'name': source.get('displayName') or f"{source.get('firstName', '')} {source.get('lastName', '')}".strip(),
                        'country': source.get('nationality') or country,
                        'gender': 'M' if source.get('gender') == 'Male' else 'F' if source.get('gender') == 'Female' else '',
                        'age': source.get('age'),
                        'birth_date': source.get('birthDate'),
                        'location': source.get('location', {}).get('display') if source.get('location') else None,
                        'utr_singles': source.get('singlesUtr'),
                        'utr_doubles': source.get('doublesUtr'),
                        'college': source.get('college') or source.get('school'),
                        'age_group': source.get('ageRange') or source.get('ageGroup'),
                        'pro_rank': source.get('proRankings', {}).get('singles') if source.get('proRankings') else None
                    }
                    
                    # Fix: If UTR is missing/0, fetch full profile (e.g. Yecong Mo case)
                    # Relaxed condition: If singles OR doubles is missing/0, not just both.
                    # Or at least if singles is missing.
                    if not p['utr_singles'] or not p['utr_doubles']:
                        try:
                            full_profile = fetch_player_profile(auth_info, pid)
                            if full_profile:
                                # Only overwrite if what we have is 0/None
                                if not p['utr_singles']:
                                    p['utr_singles'] = full_profile.get('singlesUtr')
                                if not p['utr_doubles']:
                                    p['utr_doubles'] = full_profile.get('doublesUtr')
                                    
                                # Fill other missing fields if possible
                                if not p['birth_date']: p['birth_date'] = full_profile.get('birthDate')
                                if not p['location']: p['location'] = full_profile.get('location', {}).get('display')
                                if not p['age']: p['age'] = full_profile.get('age')
                        except:
                            pass
                            
                    # Final Check for Adults: UTR must be >= 5 (User Request)
                    if category == 'adult':
                         s_utr = p.get('utr_singles') or 0
                         # If s_utr is still < 5 after potential fix, skip.
                         if s_utr < 5.0:
                             continue
                        
                    fetched.append(p)

                if len(hits) < batch_size or params['skip'] >= 480: # Limit 500
                    break
                params['skip'] += batch_size
                
            except: break
            
        return fetched

    def process_fetched_players(players):
        new_unique = []
        with player_lock:
            for p in players:
                if p['player_id'] not in all_players:
                    all_players[p['player_id']] = p
                    new_unique.append(p)
        
        if new_unique:
            save_players_incremental(new_unique)
        return len(new_unique)

    def solve_band(min_u, max_u, gender):
        # 1. Check Total
        params = {
            'top': 1, 'utrMin': min_u, 'utrMax': max_u,
            'nationality': country, 'gender': gender
        }
        if age_tag: params['ageTags'] = age_tag
        
        total = 0
        try:
             # retry logic
             r = requests.get(SEARCH_URL, params=params, headers=get_headers(auth_info), cookies=auth_info.get('cookies'), timeout=15)
             if r.status_code == 200: total = r.json().get('total', 0)
        except: pass
        
        if total == 0: return

        # Strategy Switch
        # If total is manageable, just fetch
        # API Pagination is effectively broken (limit 20), so we must split until we fit in one page
        if total <= 20: 
            players = fetch_band_with_query(min_u, max_u, gender)
            n = process_fetched_players(players)
            sys.stdout.write(f"\r   {gender} {min_u:5.2f}-{max_u:5.2f}: {n} new (n={total})     ")
            return

        # If huge but wide band, split float
        if (max_u - min_u) > 0.05: # Reduce width threshold to force splitting more
            mid = (min_u + max_u) / 2
            solve_band(min_u, mid, gender)
            solve_band(mid, max_u, gender)
            return
            
        # If huge and narrow band -> Alphabet Strategy
        # Iterate A-Z to partition the dense stack
        
        def solve_alphabet_recursive(base_query):
            # Fetch with current query
            p_list = fetch_band_with_query(min_u, max_u, gender, query=base_query)
            n = process_fetched_players(p_list)
            
            # If we hit the limit (20), we likely missed people -> recurse
            # (Note: fetch_band_with_query returns max 20 due to our limit)
            if len(p_list) >= 20: 
                # Optimization: simplistic recurse
                # If query is too long, stop to prevent infinite recursion?
                if len(base_query) >= 3: 
                    return # Stop at 3 chars (e.g. "aaa") to avoid craziness
                
                for char in alphabet:
                    solve_alphabet_recursive(base_query + char)

        for char in alphabet:
            solve_alphabet_recursive(char)
        
        # Finally, capture any odd names not in a-z (matches empty query??)
        # Actually standard recursion covers it if names contain at least one latin char.
        sys.stdout.write(f"\r   {gender} {min_u:5.2f}-{max_u:5.2f}: Dense Scan Done. Total found: {len(all_players)}    ")

    # Initial Work Items
    # Ranges: 13-16.5, 10-13, 7-10, 4-7, 1-4
    work_items = []
    
    if category == 'adult':
        # User request: Only take UTR over 5 for adults
        ranges = [(13.0, 16.5), (10.0, 13.0), (7.0, 10.0), (5.0, 7.0)]
    else:
        ranges = [(13.0, 16.5), (10.0, 13.0), (7.0, 10.0), (4.0, 7.0), (1.0, 4.0)]
        
    for g in genders:
        for r_min, r_max in ranges:
            work_items.append((r_min, r_max, g))
            
    print(f"   Starting Search with {len(work_items)} recursive roots...")
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(solve_band, u_min, u_max, g) for u_min, u_max, g in work_items]
        for f in as_completed(futures): pass

    print(f"\n   Search complete. Found {len(all_players):,} unique players.")
    return list(all_players.values())


# ============================================================================
# PHASE 1B: Scrape Matches
# ============================================================================

def fetch_player_matches(auth_info, player_id, year_filter=None):
    """Fetch matches for a player from UTR API, optionally filtered by year."""
    headers = get_headers(auth_info)
    results_url = f"https://app.utrsports.net/api/v1/player/{player_id}/results"
    
    matches = []
    skip = 0
    batch_size = 100
    stop_early = False  # Flag to stop when we've gone past the year filter
    
    while True:
        params = {'top': batch_size, 'skip': skip}
        
        try:
            resp = None
            for attempt in range(3):
                try:
                    resp = requests.get(results_url, params=params, headers=headers, 
                                       cookies=auth_info.get('cookies'), timeout=30)
                    if resp.status_code == 200:
                        break
                    elif resp.status_code == 429:
                        time.sleep(2 * (attempt + 1))
                except:
                    time.sleep(1)
            
            if not resp or resp.status_code != 200:
                break
                
            data = resp.json()
            events = data.get('events', [])
            
            if not events:
                break
            
            batch_matches_count = 0
            
            for event in events:
                event_name = event.get('name', '')
                event_date_str = event.get('startDate') or event.get('endDate')
                event_date = None
                event_year = None
                if event_date_str:
                    try:
                        dt_obj = datetime.fromisoformat(event_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                        event_date = dt_obj.date().isoformat()
                        event_year = dt_obj.year
                    except: pass
                
                # Skip events not matching the year filter
                if year_filter and event_year:
                    if event_year < year_filter:
                        stop_early = True
                        continue
                    elif event_year > year_filter:
                        continue  # Skip future years too

                for draw in event.get('draws', []):
                    draw_name = draw.get('name', '')
                    
                    for result in draw.get('results', []):
                        res_date_str = result.get('date') or result.get('resultDate')
                        match_date = None
                        match_year = None
                        if res_date_str:
                            try:
                                dt_obj = datetime.fromisoformat(res_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                                match_date = dt_obj.date().isoformat()
                                match_year = dt_obj.year
                            except: pass
                        match_date = match_date or event_date
                        match_year = match_year or event_year
                        
                        # Skip matches not in the exact year
                        if year_filter and match_year and match_year != year_filter:
                            continue
                        
                        # Check if this is a singles match (skip doubles)
                        # Doubles matches have winner2/loser2 players
                        players_data = result.get('players', {})
                        if players_data.get('winner2') or players_data.get('loser2'):
                            continue  # Skip doubles matches
                        
                        winner = players_data.get('winner1', {})
                        loser = players_data.get('loser1', {})
                        score = result.get('score', {})
                        
                        if not winner.get('id') or not loser.get('id'):
                            continue
                        
                        # Format score
                        score_str = ""
                        for i in range(1, 6):
                            s_set = score.get(str(i))
                            if s_set:
                                score_str += f"{s_set.get('winner', 0)}-{s_set.get('loser', 0)} "
                            else:
                                break
                        
                        match = {
                            'match_id': str(result.get('id')),
                            'date': match_date,
                            'winner_id': str(winner.get('id')),
                            'winner_name': winner.get('displayName') or f"{winner.get('firstName', '')} {winner.get('lastName', '')}".strip(),
                            'winner_utr': winner.get('singlesUtr'),
                            'loser_id': str(loser.get('id')),
                            'loser_name': loser.get('displayName') or f"{loser.get('firstName', '')} {loser.get('lastName', '')}".strip(),
                            'loser_utr': loser.get('singlesUtr'),
                            'score': score_str.strip(),
                            'tournament': event_name,
                            'round': draw_name
                        }
                        matches.append(match)
                        batch_matches_count += 1
            
            # Stop early if we've gone past the year filter and found no matches in batch
            if stop_early and batch_matches_count == 0:
                break
            
            skip += batch_size
            if skip > 5000:
                break
                
        except Exception as e:
            break
    
    return matches


# ============================================================================
# PHASE 1C: Scrape UTR History
# ============================================================================

def fetch_player_utr_history(auth_info, player_id):
    """Fetch UTR history for a player using V1 stats endpoint."""
    headers = get_headers(auth_info)
    history_url = f"https://app.utrsports.net/api/v1/player/{player_id}/stats"
    
    history = []
    
    # helper to fetch specific type
    def fetch_type(type_name):
        try:
            # Try 12 months first (UTR now blocks 60 months)
            params = {'type': type_name, 'resultType': 'verified', 'Months': 12}
            resp = requests.get(history_url, params=params, headers=headers, 
                               cookies=auth_info.get('cookies'), timeout=30)
            
            # If invalid timeframe (400), try shorter (6 months)
            if resp.status_code == 400:
                params['Months'] = 6
                resp = requests.get(history_url, params=params, headers=headers, 
                                   cookies=auth_info.get('cookies'), timeout=30)
            
            if resp.status_code == 200:
                data = resp.json()
                # Parse points
                points = data.get('extendedRatingProfile', {}).get('history') or data.get('ratingHistory', [])
                for point in points:
                    history.append({
                        'player_id': player_id,
                        'date': point.get('date'),
                        'rating': point.get('rating'),
                        'type': type_name
                    })
        except:
            pass

    # Fetch Singles
    fetch_type('singles')
    
    # Fetch Doubles
    fetch_type('doubles')
    
    return history


# ============================================================================
# MAIN SCRAPER
# ============================================================================

def scrape_all_data(auth_info, players, output_dir, workers=10, year_filter=None, scrape_matches=True, scrape_history=True):
    """
    Scrape matches and UTR history for all players.
    Write to JSONL files as we go.
    Deduplicates matches by match_id (same match appears for both players).
    
    Args:
        year_filter: If set, only include matches from this exact year
        scrape_matches: If True, scrape matches
        scrape_history: If True, scrape UTR history
    """
    # Open output files
    matches_file = None
    history_file = None
    
    if scrape_matches:
        matches_file = open(os.path.join(output_dir, 'matches.jsonl'), 'w', encoding='utf-8')
    if scrape_history:
        history_file = open(os.path.join(output_dir, 'utr_history.jsonl'), 'w', encoding='utf-8')
    
    file_lock = threading.Lock()
    seen_match_ids = set()  # Track seen match IDs to deduplicate
    
    stats = {
        'players_done': 0,
        'matches_written': 0,
        'matches_skipped_dupe': 0,
        'history_written': 0
    }
    stats_lock = threading.Lock()
    
    def process_player(player):
        player_id = player['player_id']
        
        matches = []
        history = []
        
        # Fetch matches (with year filter if specified)
        if scrape_matches:
            matches = fetch_player_matches(auth_info, player_id, year_filter)
        
        # Fetch UTR history
        if scrape_history:
            history = fetch_player_utr_history(auth_info, player_id)
        
        # Write to files (deduplicate matches by match_id)
        with file_lock:
            new_matches = 0
            if scrape_matches and matches_file:
                for match in matches:
                    match_id = match.get('match_id')
                    if match_id and match_id not in seen_match_ids:
                        seen_match_ids.add(match_id)
                        matches_file.write(json.dumps(match, ensure_ascii=False) + '\n')
                        new_matches += 1
                matches_file.flush()
            
            if scrape_history and history_file:
                for h in history:
                    history_file.write(json.dumps(h, ensure_ascii=False) + '\n')
                history_file.flush()

        
        with stats_lock:
            stats['players_done'] += 1
            stats['matches_written'] += new_matches
            stats['matches_skipped_dupe'] += len(matches) - new_matches
            stats['history_written'] += len(history)
        
        return len(matches), len(history)
    
    total_players = len(players)
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_player, p): p for p in players}
        
        for future in as_completed(futures):
            with stats_lock:
                done = stats['players_done']
                matches = stats['matches_written']
                history = stats['history_written']
            
            if done % 5 == 0 or done == total_players:
                pct = (done / total_players) * 100
                sys.stdout.write(f"\r   [{done}/{total_players}] {pct:.0f}% | Matches: {matches:,} | History: {history:,}")
                sys.stdout.flush()
    
    if matches_file:
        matches_file.close()
    if history_file:
        history_file.close()
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Phase 1: Scrape Players, Matches, and UTR History to files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scrape_matches_to_file.py --country CAN --category adult
    python scrape_matches_to_file.py --country CAN --category junior --year 2024
    python scrape_matches_to_file.py --country CAN --category junior --matches-only --players-file ./scrape_output/CAN_junior/players.jsonl
    python scrape_matches_to_file.py --country CAN --category adult --players-only
        """
    )
    
    parser.add_argument('--country', required=True, help='Country code (e.g., CAN, USA)')
    parser.add_argument('--category', required=True, choices=['junior', 'adult'], help='junior or adult')
    parser.add_argument('--output-dir', default='./scrape_output', help='Output directory for files')
    parser.add_argument('--workers', type=int, default=10, help='Concurrent workers (default: 10)')
    parser.add_argument('--year', type=int, default=None, help='Only scrape matches from this exact year (e.g., 2024)')
    
    # Selective scraping options
    parser.add_argument('--players-only', action='store_true', help='Only scrape players (skip matches and history)')
    parser.add_argument('--matches-only', action='store_true', help='Only scrape matches (requires --players-file)')
    parser.add_argument('--history-only', action='store_true', help='Only scrape UTR history (requires --players-file)')
    parser.add_argument('--players-file', type=str, help='Use existing players file instead of scraping (for --matches-only or --history-only)')
    
    args = parser.parse_args()
    
    # Validation
    if (args.matches_only or args.history_only) and not args.players_file:
        print("Error: --matches-only and --history-only require --players-file")
        return
    
    # Create output directory
    output_dir = os.path.join(args.output_dir, f"{args.country}_{args.category}")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"🎾 UTR Data Scraper - Phase 1 (Scrape to Files)")
    print(f"{'='*60}")
    print(f"   Country: {args.country}")
    print(f"   Category: {args.category}")
    print(f"   Output: {output_dir}")
    print(f"   Workers: {args.workers}")
    if args.year:
        print(f"   Year filter: {args.year} only")
    
    # Determine what to scrape
    scrape_players = not (args.matches_only or args.history_only)
    scrape_matches = not (args.players_only or args.history_only)
    scrape_history = not (args.players_only or args.matches_only)
    
    mode_parts = []
    if scrape_players: mode_parts.append('players')
    if scrape_matches: mode_parts.append('matches')
    if scrape_history: mode_parts.append('history')
    print(f"   Scraping: {', '.join(mode_parts)}")
    print()
    
    # Login
    auth_info = login()
    
    # =========================================
    # Step 1: Get Players (scrape or load from file)
    # =========================================
    if args.players_file:
        print(f"\n📂 Loading players from: {args.players_file}")
        players = []
        with open(args.players_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    players.append(json.loads(line.strip()))
                except:
                    pass
        print(f"   ✓ Loaded {len(players):,} players")
    else:
        if scrape_players:
            players_file = os.path.join(output_dir, 'players.jsonl')
            # Clear file if exists for fresh run, or append? Args imply fresh.
            if not args.players_file and os.path.exists(players_file):
                # Just open write to clear
                open(players_file, 'w').close()
                
            print(f"\n📊 Step 1: Scraping Players...")
            players = scrape_all_players(auth_info, args.country, args.category, output_file=players_file, workers=args.workers)
            
            if not players:
                print(f"   ✗ No players found for {args.country} / {args.category}")
                return
            
            print(f"   ✓ Found {len(players):,} players (saved incrementally to {players_file})")
    
    # =========================================
    # Step 2: Scrape Matches & UTR History
    # =========================================
    stats = {'matches_written': 0, 'matches_skipped_dupe': 0, 'history_written': 0}
    
    if scrape_matches or scrape_history:
        print(f"\n🔄 Step 2: Scraping {'Matches' if scrape_matches else ''}{' & ' if scrape_matches and scrape_history else ''}{'UTR History' if scrape_history else ''}...")
        stats = scrape_all_data(auth_info, players, output_dir, workers=args.workers, 
                               year_filter=args.year, scrape_matches=scrape_matches, scrape_history=scrape_history)
    
    # =========================================
    # Summary
    # =========================================
    print(f"\n\n{'='*60}")
    print(f"✅ Phase 1 Complete!")
    print(f"{'='*60}")
    print(f"   Players:          {len(players):,}")
    if scrape_matches:
        print(f"   Singles matches:  {stats['matches_written']:,}")
        print(f"   Duplicates skip:  {stats['matches_skipped_dupe']:,}")
    if scrape_history:
        print(f"   History records:  {stats['history_written']:,}")
    print(f"\n   Output files:")
    if scrape_players and not args.players_file:
        print(f"   - {os.path.join(output_dir, 'players.jsonl')}")
    if scrape_matches:
        print(f"   - {os.path.join(output_dir, 'matches.jsonl')}")
    if scrape_history:
        print(f"   - {os.path.join(output_dir, 'utr_history.jsonl')}")
    print(f"\n💡 Next: Run Phase 2 to bulk load into database:")
    print(f"   python load_data_to_db.py --input-dir {output_dir}")


if __name__ == "__main__":
    main()

