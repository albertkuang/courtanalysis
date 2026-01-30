
"""
Refresh Player Basic Info (Age, UTR, etc.) without fetching full match history.
Use this to quickly update the database with new fields like Age.
"""
import requests
import sys
import argparse
import tennis_db

# Reuse config from scraper (or better, import it, but copy is safer for standalone)
from config import UTR_CONFIG
CONFIG = UTR_CONFIG

LOGIN_URL = "https://app.utrsports.net/api/v1/auth/login"
SEARCH_URL = "https://app.utrsports.net/api/v2/search/players"

def login():
    print("Logging in...")
    response = requests.post(LOGIN_URL, json=CONFIG)
    if response.status_code != 200:
        raise Exception("Login failed")
    data = response.json()
    token = data.get('jwt') or data.get('token')
    if not token:
        for c in response.cookies:
            if c.name == 'jwt':
                token = c.value
    return {'token': token, 'cookies': response.cookies}

def search_players(auth_info, filters):
    params = {
        'top': filters.get('top', 100),
        'skip': filters.get('skip', 0),
        'gender': filters.get('gender'),
        'utrMin': filters.get('min_utr', 1),
        'utrMax': filters.get('max_utr', 16.5),
        'utrType': 'verified',
        'nationality': filters.get('nationality'),
    }
    if filters.get('ageTags'): params['ageTags'] = filters['ageTags']
    
    headers = {'Authorization': f"Bearer {auth_info['token']}"}
    try:
        resp = requests.get(SEARCH_URL, params=params, headers=headers, cookies=auth_info['cookies'])
        return resp.json()
    except: return {}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--country', required=True)
    parser.add_argument('--gender', default='F')
    parser.add_argument('--category', default='junior')
    args = parser.parse_args()
    
    print(f"Refreshing data for {args.country} ({args.gender})...")
    auth = login()
    tennis_db.init_db()
    conn = tennis_db.get_connection()
    
    # We will search broad bands to catch everyone
    utr_bands = [{'min': 1, 'max': 16.5}] # Just one big sweep if possible, or split if > 100 results
    # Better to split to ensure we get deep results
    utr_bands = [
        {'min': 10, 'max': 16.5},
        {'min': 8, 'max': 10},
        {'min': 6, 'max': 8},
        {'min': 1, 'max': 6}
    ]
    
    count_updated = 0
    
    for band in utr_bands:
        filters = {
            'nationality': args.country,
            'gender': args.gender,
            'min_utr': band['min'],
            'max_utr': band['max'],
            'top': 100,
            'ageTags': 'U18' if args.category == 'junior' else None
        }
        
        data = search_players(auth, filters)
        hits = data.get('hits', []) or data.get('players', [])
        
        for hit in hits:
            source = hit.get('source', hit)
            p_id = source.get('id')
            if not p_id: continue
            
            # Extract basic info
            age = source.get('age')
            # If age is missing but ageRange exists, use the lower bound
            if age is None and source.get('ageRange'):
                 try:
                     # ageRange format e.g. "19-22", "30+", "30s"
                     ar = source.get('ageRange').split('-')[0]
                     ar = ar.replace('+', '').replace('s', '').strip()
                     age = int(ar)
                 except: pass
            
            # Save to DB
            p_data = {
                'player_id': str(p_id),
                'name': source.get('displayName'),
                'gender': args.gender,
                'country': source.get('nationality'),
                'utr_singles': source.get('singlesUtr'),
                'utr_doubles': source.get('doublesUtr'),
                'age': age,
                # Preserve existing fields if not updating them, but save_player handles partials?
                # Actually save_player UPSERTs. We need to respect the schema.
            }
            # Add college logic if available in source
            p_college = source.get('playerCollege')
            if p_college:
                 p_data['college'] = p_college.get('name') if isinstance(p_college, dict) else str(p_college)
            
            tennis_db.save_player(conn, p_data)
            count_updated += 1
            
        sys.stdout.write(f"\rUpdated {count_updated} players...")
        
    conn.commit()
    print("\nRefresh complete. You can now run the export tool.")

if __name__ == "__main__":
    main()
