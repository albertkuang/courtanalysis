"""
UTR Player Scraper - Multi-Country Merge Version (Python)
Searches multiple countries and merges results to get TRUE global top juniors
"""

import requests
import csv
import sys
import argparse
from datetime import datetime

# ============================================
# ARGUMENT PARSING
# ============================================
parser = argparse.ArgumentParser(description='UTR Player Scraper')
parser.add_argument('--country', default='USA', help='ISO-3 Country Code (e.g. CAN) or ALL')
parser.add_argument('--gender', default='M', help='M or F')
parser.add_argument('--category', default='junior', help='junior, adult, or all')
parser.add_argument('--count', type=int, default=100, help='Number of players to fetch')

args = parser.parse_args()

PARAMS = {
    'COUNTRY': args.country,
    'GENDER': args.gender,
    'CATEGORY': args.category,
    'TOP_COUNT': args.count
}

# Major tennis countries to search when using --country=MAJOR
MAJOR_TENNIS_COUNTRIES = [
    'USA', 'CAN', 'GBR', 'AUS', 'FRA', 'DEU', 'ESP', 'ITA', 'JPN', 'CHN',
    'RUS', 'CZE', 'SRB', 'POL', 'NLD', 'BEL', 'SWE', 'AUT', 'SVK', 'UKR',
    'BRA', 'ARG', 'MEX', 'KOR', 'IND', 'NZL', 'ZAF', 'ISR', 'TUR', 'GRC',
    'ROU', 'HUN', 'PRT', 'CHE', 'BGR', 'HRV', 'SVN', 'LUX', 'THA', 'TWN'
]

CONFIG = {
    'email': 'alberto.kuang@gmail.com',
    'password': 'Spring2025'
}

LOGIN_URL = "https://app.utrsports.net/api/v1/auth/login"
SEARCH_URL = "https://app.utrsports.net/api/v2/search/players"

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

# ============================================
# SEARCH PLAYERS
# ============================================
def search_players(auth_info, filters):
    params = {
        'top': filters.get('top', 100),
        'skip': filters.get('skip', 0),
        'gender': filters.get('gender'),
        'utrMin': filters.get('min_utr', 1),
        'utrMax': filters.get('max_utr', 16.5),
        'utrType': 'verified'
    }
    
    if filters.get('max_utr'):
        params['utrMax'] = filters['max_utr']
    # Use ageTags for junior filtering (matches UTR API)
    if filters.get('ageTags'):
        params['ageTags'] = filters['ageTags']
    
    if filters.get('nationality'):
        params['nationality'] = filters['nationality']
    if filters.get('max_age'):
        params['maxAge'] = filters['max_age']
    
    headers = {}
    if auth_info.get('token'):
        headers['Authorization'] = f"Bearer {auth_info['token']}"
    
    try:
        response = requests.get(SEARCH_URL, params=params, headers=headers, cookies=auth_info.get('cookies'))
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {'hits': []}

# ============================================
# EXTRACT PLAYER DATA
# ============================================
def extract_player(source):
    age_range = source.get('ageRange', '')
    age = source.get('age')
    
    # Pro Rank
    pro_rank = '-'
    rankings = source.get('thirdPartyRankings', [])
    if rankings:
        rank_obj = next((r for r in rankings if r.get('source') in ['ATP', 'WTA']), rankings[0] if rankings else None)
        if rank_obj:
            pro_rank = f"{rank_obj.get('source')} #{rank_obj.get('rank')}"
    
    # College
    college = '-'
    p_college = source.get('playerCollege')
    if p_college:
        college = p_college.get('name', '-') if isinstance(p_college, dict) else str(p_college)
    elif source.get('collegeRecruiting'):
        college = 'Recruiting'
    
    # Age display
    age_display = age or age_range or '-'
    if source.get('birthDate'):
        year = source['birthDate'].split('-')[0]
        age_display = f"{year} ({age_display})"
    
    return {
        'id': source.get('id'),
        'name': source.get('displayName') or f"{source.get('firstName')} {source.get('lastName')}",
        'utr': source.get('singlesUtr') or source.get('myUtrSingles') or 0,
        'doublesUtr': source.get('doublesUtr') or source.get('myUtrDoubles') or '',
        'trend': source.get('threeMonthRatingChangeDetails', {}).get('ratingDifference'),
        'age': age_display,
        'rawAge': age,
        'ageRange': age_range,
        'location': (source.get('location') or {}).get('display') or source.get('city') or '',
        'nationality': source.get('nationality'),
        'proRank': pro_rank,
        'college': college,
        'profileUrl': f"https://app.utrsports.net/profiles/{source.get('id')}"
    }

# ============================================
# MAIN
# ============================================
def main():
    print("================================================================")
    print("          UTR PLAYER SCRAPER (Multi-Country Merge)")
    print("================================================================")
    print(f"Country={PARAMS['COUNTRY']}, Gender={PARAMS['GENDER']}, Category={PARAMS['CATEGORY']}, Count={PARAMS['TOP_COUNT']}\n")
    
    auth_info = login()
    target_count = PARAMS['TOP_COUNT']
    all_players = []
    seen_ids = set()
    
    # Determine search mode: ALL (global), MAJOR (40 countries), or specific country
    is_global_search = PARAMS['COUNTRY'] == 'ALL' or PARAMS['COUNTRY'] == ''
    is_major_search = PARAMS['COUNTRY'] == 'MAJOR'
    
    countries = MAJOR_TENNIS_COUNTRIES if is_major_search else ([None] if is_global_search else [PARAMS['COUNTRY']])
    
    if is_global_search:
        print("Searching GLOBALLY (all countries) for top players...\n")
    elif is_major_search:
        print(f"Searching {len(MAJOR_TENNIS_COUNTRIES)} major tennis countries...\n")
    else:
        print(f"Searching country: {PARAMS['COUNTRY']}...\n")
    
    for country in countries:
        if country:
            sys.stdout.write(f"Searching {country}... ")
        else:
            sys.stdout.write(f"Global search... ")
        sys.stdout.flush()
        
        # Use UTR banding to get more results
        utr_bands = [
            {'min': 10, 'max': 16.5},
            {'min': 9, 'max': 10},
            {'min': 8, 'max': 9},
            {'min': 7, 'max': 8},
            {'min': 6, 'max': 7},
            {'min': 5, 'max': 6},
            {'min': 1, 'max': 5}
        ]
        
        country_added = 0
        
        for band in utr_bands:
            filters = {
                'nationality': country,
                'gender': PARAMS['GENDER'],
                'min_utr': band['min'],
                'max_utr': band['max'],
                'ageTags': 'U18' if PARAMS['CATEGORY'] == 'junior' else None,
                'top': 100
            }
            
            results = search_players(auth_info, filters)
            hits = results.get('hits', []) or results.get('players', [])
            
            for hit in hits:
                source = hit.get('source', hit)
                if source.get('id') in seen_ids:
                    continue
                
                player = extract_player(source)
                
                # Category filter
                if PARAMS['CATEGORY'] == 'junior':
                    if player['rawAge'] and player['rawAge'] > 18:
                        continue
                    if not player['rawAge'] and player['ageRange']:
                        import re
                        if re.match(r'^(19|2|3|4|5)', player['ageRange']):
                            continue
                
                seen_ids.add(source.get('id'))
                all_players.append(player)
                country_added += 1
        
        print(f"{country_added} players")
    
    # Sort by UTR descending
    all_players.sort(key=lambda x: x.get('utr') or 0, reverse=True)
    
    # Take top N
    final_players = all_players[:target_count]
    
    print(f"\nCollected {len(all_players)} total players, selecting top {len(final_players)}")
    
    # Display top 20
    print('\n' + '=' * 100)
    country_label = 'WORLD' if PARAMS['COUNTRY'] == 'ALL' else PARAMS['COUNTRY']
    gender_label = 'GIRLS' if PARAMS['GENDER'] == 'F' else 'BOYS'
    print(f"TOP {len(final_players)} {PARAMS['CATEGORY'].upper()} {gender_label} ({country_label})")
    print('=' * 100)
    
    for i, p in enumerate(final_players[:20]):
        print(f"{str(i+1).rjust(3)}. {p['name'][:25].ljust(25)} UTR: {str(p['utr']).ljust(6)} {(p['nationality'] or '').ljust(4)} {p['proRank'].ljust(12)}")
    
    if len(final_players) > 20:
        print(f"    ... and {len(final_players) - 20} more")
    
    # Save CSV
    date_str = datetime.now().strftime("%Y%m%d")
    country_str = 'World' if (PARAMS['COUNTRY'] == 'ALL' or PARAMS['COUNTRY'] == '') else PARAMS['COUNTRY']
    gender_str = 'Male' if PARAMS['GENDER'] == 'M' else 'Female'
    filename = f"{country_str}_{PARAMS['CATEGORY']}_{gender_str}_ANALYST_{date_str}.csv"
    
    headers = ['Rank', 'Name', 'Singles UTR', 'Doubles UTR', '3-Month Trend', 'Age', 'Country', 'Location', 'Pro Rank', 'College', 'Profile URL']
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for i, p in enumerate(final_players):
            trend = f"{p['trend']:.2f}" if p['trend'] is not None else ''
            writer.writerow([
                i + 1,
                p['name'],
                p['utr'],
                p['doublesUtr'],
                trend,
                p['age'],
                p['nationality'] or '',
                p['location'],
                p['proRank'],
                p['college'],
                p['profileUrl']
            ])
    
    print(f"\nSaved to: {filename}")
    print(f"Done! {len(final_players)} players scraped.")

if __name__ == "__main__":
    main()
