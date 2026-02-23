"""
College Player Active Flag Population - Bulk Roster Fetch
Uses UTR API to fetch full college rosters and update players' active status.
"""

import requests
import json
import time
from datetime import datetime
import argparse
import sys
import sqlite3
from config import UTR_CONFIG

# Configuration
LOGIN_URL = "https://app.utrsports.net/api/v1/auth/login"
COLLEGE_SEARCH_URL = "https://app.utrsports.net/api/v2/search/colleges"
ROSTER_URL_TEMPLATE = "https://app.utrsports.net/api/v1/club/{}/members"

# ============================================
# LOGIN
# ============================================
def login():
    print("Logging in to UTR...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Content-Type": "application/json"
    }
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
    
    print("Login successful!")
    return {'token': token, 'cookies': response.cookies}

# ============================================
# FIND COLLEGE
# ============================================
def find_college_by_name(auth_info, name, preferred_gender='M'):
    headers = {}
    if auth_info.get('token'):
        headers['Authorization'] = f"Bearer {auth_info['token']}"
    
    params = {'query': name, 'top': 20}
    
    try:
        response = requests.get(COLLEGE_SEARCH_URL, params=params, headers=headers, cookies=auth_info.get('cookies'))
        if response.status_code != 200: return None
            
        data = response.json()
        hits = data.get('hits', [])
        
        target_hit = None
        for hit in hits:
            source = hit.get('source', hit)
            h_name = source.get('name', '').lower()
            if name.lower() in h_name or h_name in name.lower():
                target_hit = source
                break
            if name.lower() in h_name or h_name in name.lower():
                if not target_hit: target_hit = source
        
        if not target_hit and hits:
             # Fallback to first hit if no good match
             target_hit = hits[0].get('source', hits[0])

        if target_hit:
            m_id = target_hit.get('mensClubId')
            w_id = target_hit.get('womensClubId')
            club_id = target_hit.get('clubId') or target_hit.get('id')
            
            # Default to gender specific, but keep others available
            primary_id = club_id
            if preferred_gender == 'M' and m_id: primary_id = m_id
            elif preferred_gender == 'F' and w_id: primary_id = w_id
                
            return {
                'name': target_hit.get('name'),
                'id': target_hit.get('id'),
                'clubId': primary_id,
                'fallbackId': club_id if club_id != primary_id else None
            }
    except Exception as e:
        print(f"Error finding college {name}: {e}")
        
    return None

# ============================================
# GET ROSTER
# ============================================
def get_college_roster(auth_info, club_id, gender, division='d1'):
    headers = {}
    if auth_info.get('token'):
        headers['Authorization'] = f"Bearer {auth_info['token']}"
        
    roster = []
    skip = 0
    batch_size = 100
    current_year = datetime.now().year
    
    while True:
        params = {
            'top': batch_size,
            'skip': skip,
            'gender': 'M' if gender == 'M' else 'F',
            'utrType': 'verified',
            'clubId': club_id
        }
        
        try:
            response = requests.get("https://app.utrsports.net/api/v2/search/players", params=params, headers=headers, cookies=auth_info.get('cookies'))
            if response.status_code != 200: break
                
            data = response.json()
            hits = data.get('hits', [])
            
            if not hits: break
            
            for hit in hits:
                m = hit.get('source', hit)
                
                if 'Praneel' in m.get('displayName', ''):
                    print(f"\n*** FOUND PRANEEL: {m.get('displayName')} ***")
                    print(json.dumps(m, indent=2))
                
                # Active Check
                col_details = m.get('playerCollegeDetails')
                is_active = False
                grad_year = m.get('gradYear')
                
                # Debug specific player to trace logic
                # if 'Diego' in m.get('displayName', ''):
                #    print(f"DEBUG: Checking {m.get('displayName')} - GY: {grad_year}, CD: {col_details}")
                
                is_active = False
                is_explicitly_inactive = False
                
                # Check 1: College Details
                if col_details:
                    gy_str = col_details.get('gradYear')
                    if gy_str:
                         try:
                             gy = int(gy_str.split('-')[0])
                             if gy >= current_year: is_active = True
                             else: is_explicitly_inactive = True
                         except: 
                             # If we can't parse, but details exist -> lean active
                             is_active = True
                    else: 
                        # Details exist but no year -> lean active
                        is_active = True
                
                # Check 2: Top-level Grad Year (if not decided)
                if not is_active and not is_explicitly_inactive and grad_year:
                    try:
                        gy = int(grad_year)
                        if current_year < gy <= current_year + 5: 
                            is_active = True
                        elif gy == current_year:
                            # TIGHTEN: If it's the current year, we MUST have college details to be "active"
                            # for college. Otherwise it's likely an HS senior recruit.
                            if col_details:
                                is_active = True
                            else:
                                pass # Stay inactive
                        elif gy < current_year: is_explicitly_inactive = True
                    except: pass

                # Final Decision Logic
                if is_active:
                    pass
                elif is_explicitly_inactive:
                    continue 
                else:
                    # Ambiguous case: No explicit college details or grad year match
                    if division.lower() == 'd1':
                        # D1 is usually well-maintained. If no details, assume HS Senior/Pro/Alumnus.
                        continue
                    
                    utr_check = m.get('singlesUtr', 0) or 0
                    
                    # 1. Filter high-UTR pros/alumni without details
                    if utr_check > 14.1:
                        continue
                        
                    # 2. Filter High Schoolers / Recruits
                    if grad_year:
                        try:
                            gy = int(grad_year)
                            if gy == current_year: continue # Likely HS Senior if no details
                            if gy > current_year + 4: continue # Too far out
                        except: pass
                    
                    # 3. Default for remaining D2/D3 low-data players
                    is_active = True

                # UTR Check
                utr = m.get('singlesUtr', 0) or 0
                d_utr = m.get('doublesUtr', 0) or 0
                
                # ALLOW 0 UTR players (often placeholder roster entries for D2/D3)
                # if utr == 0 and d_utr == 0: continue

                roster.append({
                    'id': str(m.get('id')),
                    'name': m.get('displayName'),
                    'gradYear': grad_year,
                    'utr': utr,
                    'doublesUtr': d_utr
                })
            
            if len(hits) < batch_size: break
            skip += batch_size
            
        except Exception as e:
            print(f"Error fetching page: {e}")
            break
            
    return roster

# ============================================
# MAIN
# ============================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--division', choices=['d1', 'd2', 'd3', 'all'], default='d1', help='Division to process')
    parser.add_argument('--gender', default='M', help='M or F')
    parser.add_argument('--limit', type=int, default=0, help='Max colleges to process')
    parser.add_argument('--file', help='Specific file to read colleges from')
    args = parser.parse_args()
    
    auth_info = login()
    
    conn = sqlite3.connect('tennis_data.db')
    cursor = conn.cursor()
    
    colleges = []
    
    if args.file:
         with open(args.file, 'r', encoding='utf-8-sig') as f:
            colleges = [line.strip() for line in f if line.strip()]
    else:
        files_map = {
            'd1': ['d1_colleges.txt'],
            'd2': ['d2_colleges.txt'],
            'd3': ['d3_colleges.txt'],
            'all': ['d1_colleges.txt', 'd2_colleges.txt', 'd3_colleges.txt']
        }
        target_files = files_map[args.division.lower()]
        for filepath in target_files:
            try:
                print(f"Reading {filepath}...", end='')
                with open(filepath, 'r', encoding='utf-8-sig') as f:
                    file_colleges = [line.strip() for line in f if line.strip()]
                    colleges.extend(file_colleges)
                print(f" Added {len(file_colleges)} colleges.")
            except FileNotFoundError:
                print(f"\nWarning: File {filepath} not found.")

    # Remove duplicates if any
    colleges = sorted(list(set(colleges)))
        
    if args.limit > 0:
        colleges = colleges[:args.limit]
        
    print(f"Processing {len(colleges)} unique colleges...")
    
    total_updated = 0
    total_new = 0
    
    for i, col_name in enumerate(colleges):
        # 1. Search College
        print(f"[{i+1}/{len(colleges)}] {col_name}...", end='', flush=True)
        
        col_info = find_college_by_name(auth_info, col_name, args.gender)
        if not col_info:
            print(" Not found (search).")
            continue

        # 1b. Reset active status for this college to prevent stale data
        # Only reset if we actually found the college
        cursor.execute("UPDATE players SET is_active_college = 0 WHERE college_id = ?", (col_info['id'],))
        conn.commit()

        # 2. Get Roster
        roster_active = get_college_roster(auth_info, col_info['clubId'], args.gender, division=args.division)
        
        if not roster_active and col_info.get('fallbackId'):
            print(f" (Retry {col_info['fallbackId']})...", end='', flush=True)
            roster_active = get_college_roster(auth_info, col_info['fallbackId'], args.gender, division=args.division)
        
        # 3. Stats
        if not roster_active:
            print(f" Found 0 active players (ClubID: {col_info['clubId']}).")
            continue
            
        print(f" Found {len(roster_active)} active players.", end='', flush=True)
        
        # 4. Update DB
        updated_count = 0
        new_count = 0
        
        for p in roster_active:
            cursor.execute("SELECT player_id FROM players WHERE player_id = ?", (p['id'],))
            existing = cursor.fetchone()
            
            now = datetime.now().isoformat()
            
            if existing:
                cursor.execute("""
                    UPDATE players 
                    SET is_active_college = 1, 
                        college_name = ?, 
                        college_id = ?, 
                        grad_year = ?,
                        division = ?,
                        last_college_check = ?
                    WHERE player_id = ?
                """, (col_info['name'], col_info['id'], p['gradYear'], args.division.upper(), now, p['id']))
                updated_count += 1
            else:
                # Insert new skeleton player
                cursor.execute("""
                    INSERT INTO players (player_id, name, college_name, college_id, grad_year, division, is_active_college, gender, utr_singles, utr_doubles, last_college_check)
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                """, (p['id'], p['name'], col_info['name'], col_info['id'], p['gradYear'], args.division.upper(), args.gender, p['utr'], p['doublesUtr'], now))
                new_count += 1
                
        conn.commit()
        print(f" -> Updated: {updated_count}, New: {new_count}")
        total_updated += updated_count
        total_new += new_count
        
        # Rate limit
        time.sleep(0.5)
        
    conn.close()
    print(f"\nDone. Total updated: {total_updated}, Total new: {total_new}")

if __name__ == "__main__":
    main()
