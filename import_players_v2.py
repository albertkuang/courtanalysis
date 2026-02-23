"""
Efficient UTR Player Importer
Retrieves player info and metrics from UTR API and saves to database.

Features:
- Supports ALL countries or specific country code
- Gender filter (M/F)
- Category filter (junior/adult/college)
- Min/Max UTR range
- Outputs each player to terminal
- Fetches players in UTR descending order
- Efficient recursive band-splitting to overcome API pagination limits
"""

import requests
import sys
import argparse
import time
import tennis_db
import concurrent.futures
from typing import Optional, Dict, List
from config import UTR_CONFIG

# Configuration
CONFIG = UTR_CONFIG
LOGIN_URL = "https://app.utrsports.net/api/v1/auth/login"
SEARCH_URL = "https://app.utrsports.net/api/v2/search/players"

class UTRPlayerImporter:
    def __init__(self, country: str = "CAN", gender: str = None, category: str = "junior",
                 min_utr: float = 4.0, max_utr: float = 16.5, max_workers: int = 10,
                 update_existing: bool = True, display_only: bool = False):
        self.country = country.upper() if country != "ALL" else None
        self.gender = gender.upper() if gender else None
        self.category = category.lower()
        self.min_utr = min_utr
        self.max_utr = max_utr
        self.max_workers = max_workers
        self.update_existing = update_existing
        self.display_only = display_only
        
        self.auth_info = None
        self.conn = None
        self.seen_ids = set()
        self.total_processed = 0
        self.total_saved = 0
        self.total_updated = 0
        
    def login(self):
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
            self.auth_info = {'token': token, 'cookies': response.cookies}
            return True
        except Exception as e:
            print(f"Login Error: {e}")
            return False
    
    def search_players(self, filters: Dict) -> Dict:
        """Search for players with given filters"""
        params = {
            'top': 100,
            'utrMin': filters.get('min_utr', 1),
            'utrMax': filters.get('max_utr', 16.5),
            'utrType': 'verified'
        }
        
        if filters.get('top'):
            params['top'] = filters['top']
        if filters.get('skip'):
            params['skip'] = filters['skip']
        
        # Add filters only if specified
        if filters.get('gender'):
            params['gender'] = filters['gender']
        if filters.get('nationality'):
            params['nationality'] = filters['nationality']
        if filters.get('ageTags'):
            params['ageTags'] = filters['ageTags']
        if filters.get('query'):
            params['query'] = filters['query']
            
        headers = {
            'Authorization': f"Bearer {self.auth_info['token']}",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
        }
        
        try:
            response = requests.get(SEARCH_URL, params=params, headers=headers, 
                                   cookies=self.auth_info.get('cookies'), timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"  Search returned status {response.status_code}")
        except Exception as e:
            print(f"Search Error: {e}")
        return {'hits': [], 'total': 0}
    
    def process_player(self, source: Dict) -> bool:
        """Process and save a single player"""
        conn = tennis_db.get_connection()
        try:
            player_id = str(source.get('id'))
            name = source.get('displayName') or f"{source.get('firstName')} {source.get('lastName')}"
            
            # Basic Info
            player_data = {
                'player_id': player_id,
                'name': name,
                'country': source.get('nationality'),
                'gender': source.get('gender'),
                'utr_singles': source.get('singlesUtr') or source.get('myUtrSingles') or 0,
                'utr_doubles': source.get('doublesUtr') or source.get('myUtrDoubles') or 0,
                'location': (source.get('location') or {}).get('display') or source.get('city'),
                'age_group': source.get('ageRange', ''),
                'age': source.get('age')
            }
            
            # Normalize gender
            if player_data['gender'] == 'Male': player_data['gender'] = 'M'
            elif player_data['gender'] == 'Female': player_data['gender'] = 'F'
            
            headers = {'Authorization': f"Bearer {self.auth_info['token']}"}
            
            # Fetch V2 Profile for accurate age/DOB
            try:
                v2_url = f"https://app.utrsports.net/api/v2/player/{player_id}"
                v2_res = requests.get(v2_url, headers=headers, cookies=self.auth_info.get('cookies'), timeout=15)
                if v2_res.status_code == 200:
                    v2 = v2_res.json()
                    player_data['birth_date'] = v2.get('birthDate')
                    if v2.get('age'):
                        player_data['age'] = v2.get('age')
                    if v2.get('location') and isinstance(v2.get('location'), dict):
                        player_data['location'] = v2.get('location').get('display')
            except: pass
            
            # Fetch match stats for metrics
            try:
                results_url = f"https://app.utrsports.net/api/v1/player/{player_id}/results"
                r_params = {'top': 50}
                r_res = requests.get(results_url, params=r_params, headers=headers, 
                                    cookies=self.auth_info.get('cookies'), timeout=15)
                
                comeback_wins = 0
                tiebreak_wins = 0
                tiebreak_losses = 0
                three_set_wins = 0
                three_set_losses = 0
                
                if r_res.status_code == 200:
                    r_data = r_res.json()
                    for event in r_data.get('events', []):
                        for draw in event.get('draws', []):
                            for result in draw.get('results', []):
                                winner = result.get('players', {}).get('winner1', {})
                                loser = result.get('players', {}).get('loser1', {})
                                score = result.get('score', {})
                                
                                is_winner = str(winner.get('id')) == player_id
                                is_loser = str(loser.get('id')) == player_id
                                
                                if not is_winner and not is_loser: continue
                                
                                num_sets = len(score) if score else 0
                                if num_sets >= 3:
                                    if is_winner: three_set_wins += 1
                                    else: three_set_losses += 1
                                
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
                                
                                if is_winner and score and '1' in score:
                                    first_set = score['1']
                                    if first_set and first_set.get('winner', 0) < first_set.get('loser', 0):
                                        comeback_wins += 1
                                        
                player_data['comeback_wins'] = comeback_wins
                player_data['tiebreak_wins'] = tiebreak_wins
                player_data['tiebreak_losses'] = tiebreak_losses
                player_data['three_set_wins'] = three_set_wins
                player_data['three_set_losses'] = three_set_losses
            except: pass
            
            if not self.display_only:
                # Save to DB
                tennis_db.save_player(conn, player_data)
                conn.commit()
            
            # Output to terminal
            utr = player_data['utr_singles'] or 0
            age = player_data.get('age') or player_data.get('age_group') or 'N/A'
            country = player_data.get('country') or 'N/A'
            gender = player_data.get('gender') or 'N/A'
            prefix = " (DISPLAY)" if self.display_only else "  +"
            print(f" {prefix} {name:<30} UTR: {utr:>5.2f}  Age: {str(age):<6}  {gender}  {country}")
            
            return True
            
        except Exception as e:
            print(f"  X Error saving {source.get('displayName')}: {e}")
            return False
        finally:
            conn.close()
    
    def scan_band(self, band_min: float, band_max: float, gender: str, query_char: str = None) -> int:
        """
        Recursively scan a UTR band for players.
        Strategy (matches scrape_matches_to_file.py):
        1. First check total with lightweight query (top=1)
        2. If total <= 450, fetch directly
        3. If total > 450 and band wide enough (>0.1), split UTR band
        4. If total > 450 and band narrow, use alphabet (a-z)
        Returns number of players processed.
        """
        # Step 1: Lightweight total check
        check_params = {
            'top': 1,
            'skip': 0,
            'utrMin': band_min,
            'utrMax': band_max,
            'gender': gender
        }
        
        if self.country:
            check_params['nationality'] = self.country
            
        if self.category == 'junior':
            check_params['ageTags'] = 'U18'
        elif self.category == 'college':
            check_params['ageTags'] = 'college'
        
        # Check total first
        check_results = self.search_players(check_params)
        total_in_band = check_results.get('total', 0)
        
        # DEBUG: Log API response for troubleshooting
        print(f"DEBUG: check_params={check_params}")
        print(f"DEBUG: total_in_band={total_in_band}")
        
        if total_in_band == 0:
            return 0
        
        # Step 2: If total is manageable, fetch directly
        if total_in_band <= 450:
            filters = {
                'min_utr': band_min,
                'max_utr': band_max,
                'gender': gender,
                'top': 100,
                'skip': 0
            }
            if self.country:
                filters['nationality'] = self.country
            if self.category == 'junior':
                filters['ageTags'] = 'U18'
            elif self.category == 'college':
                filters['ageTags'] = 'college'
            if query_char:
                filters['query'] = query_char
            
            results = self.search_players(filters)
            hits = results.get('hits', []) or results.get('players', [])
            
            # Pagination to get all results
            if len(hits) < total_in_band and len(hits) < 500:
                current_skip = len(hits)
                while current_skip < total_in_band and current_skip < 500:
                    filters['skip'] = current_skip
                    filters['top'] = 100
                    next_res = self.search_players(filters)
                    next_hits = next_res.get('hits', []) or next_res.get('players', [])
                    if not next_hits: break
                    hits.extend(next_hits)
                    current_skip = len(hits)
        else:
            # Step 3: If huge but wide band, split UTR
            if (band_max - band_min) > 0.1:
                mid = (band_min + band_max) / 2
                qstr = f" [{query_char}]" if query_char else ""
                print(f"  Band {band_min:.2f}-{band_max:.2f}{qstr}: {total_in_band} players (splitting)")
                self.scan_band(band_min, mid, gender, query_char)
                self.scan_band(mid, band_max, gender, query_char)
                return 0
            
            # Step 4: If huge and narrow band -> Alphabet Strategy
            if not query_char:
                print(f"  Band {band_min:.3f}-{band_max:.3f}: {total_in_band} players (alphabet scan)")
                for char in 'abcdefghijklmnopqrstuvwxyz':
                    self.scan_band(band_min, band_max, gender, char)
                return 0
            else:
                # Already into alphabet and still dense? Try deeper splitting (rare)
                if (band_max - band_min) > 0.01:
                    mid = round((band_min + band_max) / 2, 4)
                    self.scan_band(mid, band_max, gender, query_char)
                    self.scan_band(band_min, mid, gender, query_char)
                    return 0
            
            # If we get here with alphabet query and very narrow band, try to fetch anyway
            filters = {
                'min_utr': band_min,
                'max_utr': band_max,
                'gender': gender,
                'top': 100,
                'skip': 0,
                'query': query_char
            }
            if self.country:
                filters['nationality'] = self.country
            if self.category == 'junior':
                filters['ageTags'] = 'U18'
            elif self.category == 'college':
                filters['ageTags'] = 'college'
            
            results = self.search_players(filters)
            hits = results.get('hits', []) or results.get('players', [])
        
        if not hits:
            return 0
        
        print(f"DEBUG: Processing {len(hits)} hits in band {band_min}-{band_max}")
        # Process players - filter and collect
        players_to_process = []
        skipped_out_of_range = 0
        skipped_duplicate = 0
        skipped_in_db = 0
        skipped_category = 0
        
        for hit in hits:
            source = hit.get('source', hit)
            pid = str(source.get('id'))
            
            if pid in self.seen_ids:
                skipped_duplicate += 1
                continue
            self.seen_ids.add(pid)
            
            # Skip players with no verified UTR
            utr = source.get('singlesUtr') or source.get('myUtrSingles') or 0
            if utr == 0 or utr < 0.1:
                continue
            
            # UTR API doesn't strictly enforce utrMin/utrMax - filter client-side
            if utr < self.min_utr or utr > self.max_utr:
                skipped_out_of_range += 1
                continue
            
            # Additional category filtering - Match scrape_matches_to_file.py logic
            if self.category == 'junior':
                age_range = source.get('ageRange') or source.get('ageGroup') or ''
                if age_range and any(x in age_range for x in ['19', '2', '3', '4', '5']):
                    skipped_category += 1
                    continue
            elif self.category == 'adult':
                age_range = source.get('ageRange') or source.get('ageGroup') or ''
                
                # Strict Age Group Allowlist (Matches scrape_matches_to_file.py)
                allowed_groups = ['19-22', '23-29', '30s']
                if age_range not in allowed_groups:
                    # DEBUG: print(f"    [SKIP] {source.get('displayName')} (age_group='{age_range}' not in allowed)")
                    skipped_category += 1
                    continue

                # Hard UTR Limit for Adults
                if utr < 5.0:
                    skipped_out_of_range += 1
                    continue
            
            # print(f"    [SUCCESS] {source.get('displayName')} ({utr})")

            
            if self.display_only:
                # FAST DISPLAY: Print directly from hit, skip profile/match fetches
                utr = source.get('singlesUtr') or source.get('myUtrSingles') or 0
                age_str = source.get('age') or source.get('ageRange') or source.get('ageGroup') or 'N/A'
                country = source.get('nationality') or 'N/A'
                g_str = 'M' if source.get('gender') == 'Male' else 'F' if source.get('gender') == 'Female' else source.get('gender') or 'N'
                display_name = source.get('displayName') or f"{source.get('firstName')} {source.get('lastName')}"
                print(f"  [DISPLAY] {pid:<10} {display_name:<25} UTR: {utr:>5.2f}  Age: {str(age_str):<8}  {g_str}  {country}")
                players_to_process.append({'source': source, 'is_update': False}) # Track for total count
                continue

            # Check if already in DB
            c = self.conn.cursor()
            c.execute("SELECT 1 FROM players WHERE player_id = ?", (pid,))
            exists = c.fetchone() is not None
            
            if exists and not self.update_existing:
                skipped_in_db += 1
                continue
            
            players_to_process.append({'source': source, 'is_update': exists})
        
        # Print band info with actual stats
        qstr = f" [{query_char}]" if query_char else ""
        if players_to_process:
            print(f"  Band {band_min:.3f}-{band_max:.3f}{qstr}: {len(players_to_process)} new", end="")
            if skipped_out_of_range > 0:
                print(f" (skipped {skipped_out_of_range} OOR)", end="")
            if skipped_in_db > 0:
                print(f" (skipped {skipped_in_db} DB)", end="")
            if skipped_duplicate > 0:
                print(f" (skipped {skipped_duplicate} DUP)", end="")
            if skipped_category > 0:
                print(f" (skipped {skipped_category} CAT)", end="")
            print()
        elif skipped_in_db > 0 or skipped_duplicate > 0 or skipped_category > 0:
             # If we processed 0 candidates but found matches that were skipped
             print(f"  Band {band_min:.3f}-{band_max:.3f}{qstr}: 0 new (skipped {skipped_in_db} DB, {skipped_duplicate} DUP, {skipped_category} CAT)")
        
        if players_to_process and not self.display_only:
            # Sort by UTR descending before processing
            players_to_process.sort(key=lambda x: x['source'].get('singlesUtr') or x['source'].get('myUtrSingles') or 0, reverse=True)
            
            # Process with thread pool
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(self.process_player, p['source']): p['is_update'] for p in players_to_process}
                for future in concurrent.futures.as_completed(futures):
                    is_update = futures[future]
                    if future.result():
                        if is_update:
                            self.total_updated += 1
                        else:
                            self.total_saved += 1
                    self.total_processed += 1
        elif self.display_only:
            self.total_processed += len(players_to_process)
        
        return len(players_to_process)
    
    def run(self):
        """Main import function"""
        if not self.login():
            return
        
        tennis_db.init_db()
        self.conn = tennis_db.get_connection()
        
        country_display = self.country if self.country else "ALL COUNTRIES"
        gender_display = self.gender if self.gender else "ALL"
        
        print(f"\n{'='*60}")
        print(f"UTR Player Import")
        print(f"{'='*60}")
        print(f"Country:  {country_display}")
        print(f"Gender:   {gender_display}")
        print(f"Category: {self.category}")
        print(f"UTR Range: {self.min_utr} - {self.max_utr}")
        print(f"Workers:  {self.max_workers}")
        print(f"Update existing: {self.update_existing}")
        print(f"{'='*60}\n")
        
        # Determine genders to process
        genders = [self.gender] if self.gender else ['M', 'F']
        
        # Create UTR bands from max to min (3.0-width initial bands, matching scrape_matches_to_file.py)
        if self.category == 'adult' and self.min_utr < 5.0:
            print(f"   [INFO] Enforcing min_utr=5.0 for Adult category (per configuration).")
            self.min_utr = 5.0
            
        bands = []
        current_max = self.max_utr
        while current_max > self.min_utr:
            current_min = max(self.min_utr, current_max - 3.0)
            # Ensure we don't get stuck
            if current_min >= current_max: break
            bands.append({'min': current_min, 'max': current_max})
            current_max = current_min
        
        print(f"   Starting Search with {len(bands) * len(genders)} recursive roots ({self.min_utr}-{self.max_utr})...")
        
        for gender in genders:
            gender_name = "Male" if gender == "M" else "Female"
            print(f"\n--- {gender_name} Players ---")
            
            for band in bands:
                self.scan_band(band['min'], band['max'], gender)
        
        print(f"\n{'='*60}")
        print(f"Import Complete!")
        print(f"Total Processed: {self.total_processed}")
        print(f"New Players Saved: {self.total_saved}")
        print(f"Existing Players Updated: {self.total_updated}")
        print(f"{'='*60}")
        
        self.conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Efficient UTR Player Importer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import all Canadian juniors with UTR 8+
  python import_players_v2.py --country CAN --category junior --min-utr 8

  # Import all USA adult females
  python import_players_v2.py --country USA --category adult --gender F

  # Import players from all countries
  python import_players_v2.py --country ALL --category adult
        """
    )
    
    parser.add_argument('--country', default='CAN', 
                        help='Country code (e.g., CAN, USA) or ALL for all countries (default: CAN)')
    parser.add_argument('--gender', choices=['M', 'F'], default=None,
                        help='Gender filter: M or F (default: both)')
    parser.add_argument('--category', choices=['junior', 'adult', 'college'], default='junior',
                        help='Category: junior, adult, or college (default: junior)')
    parser.add_argument('--min-utr', type=float, default=4.0,
                        help='Minimum UTR (default: 4.0)')
    parser.add_argument('--max-utr', type=float, default=16.5,
                        help='Maximum UTR (default: 16.5)')
    parser.add_argument('--workers', type=int, default=10,
                        help='Number of concurrent workers (default: 10)')
    parser.add_argument('--no-update', action='store_true',
                        help='Skip existing players, only add new ones')
    parser.add_argument('--display-only', action='store_true',
                        help='Display players in terminal only, do not save to database')
    
    args = parser.parse_args()
    
    # Determine update mode
    update_existing = not args.no_update
    
    importer = UTRPlayerImporter(
        country=args.country,
        gender=args.gender,
        category=args.category,
        min_utr=args.min_utr,
        max_utr=args.max_utr,
        max_workers=args.workers,
        update_existing=update_existing,
        display_only=args.display_only
    )
    
    importer.run()


if __name__ == "__main__":
    main()
