#!/usr/bin/env python3
"""
Import Jeff Sackmann's tennis match data from GitHub into the database.

Sources:
- https://github.com/JeffSackmann/tennis_atp
- https://github.com/JeffSackmann/tennis_wta

Usage:
    python import_sackmann.py --tour atp --start 2020 --end 2024
    python import_sackmann.py --tour wta --start 2015 --end 2024
    python import_sackmann.py --tour atp-challengers --start 2020 --end 2024
    python import_sackmann.py --tour all --start 2015 --end 2024
"""

import argparse
import csv
import io
import sqlite3
import requests
from datetime import datetime
from difflib import SequenceMatcher
import tennis_db

# GitHub raw URLs
ATP_BASE = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master"
WTA_BASE = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master"

# File patterns
FILE_PATTERNS = {
    'atp': (ATP_BASE, 'atp_matches_{year}.csv'),
    'wta': (WTA_BASE, 'wta_matches_{year}.csv'),
    'atp-challengers': (ATP_BASE, 'atp_matches_qual_chall_{year}.csv'),
    'wta-challengers': (WTA_BASE, 'wta_matches_qual_itf_{year}.csv'),
    'atp-futures': (ATP_BASE, 'atp_matches_futures_{year}.csv'),
}

# Stats columns to import
STATS_COLS = [
    'w_ace', 'w_df', 'w_svpt', 'w_1stIn', 'w_1stWon', 'w_2ndWon', 'w_SvGms', 'w_bpSaved', 'w_bpFaced',
    'l_ace', 'l_df', 'l_svpt', 'l_1stIn', 'l_1stWon', 'l_2ndWon', 'l_SvGms', 'l_bpSaved', 'l_bpFaced',
]


def get_db_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect(tennis_db.DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def download_csv(url):
    """Download a CSV file and return its content."""
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"  Failed to download {url}: {e}")
        return None


def normalize_name(name):
    """Normalize a player name for matching."""
    if not name:
        return ""
    # Remove accents and special chars, lowercase
    name = name.lower().strip()
    # Handle common variations
    name = name.replace(".", "").replace("-", " ").replace("'", "")
    # Remove extra spaces
    name = " ".join(name.split())
    return name


def fuzzy_match_score(name1, name2):
    """Get fuzzy match score between two names."""
    return SequenceMatcher(None, normalize_name(name1), normalize_name(name2)).ratio()


def find_matching_player(conn, sackmann_name, sackmann_id, country=None):
    """
    Find a matching player in the database.
    Returns (player_id, match_type) or (None, None) if no match.
    """
    c = conn.cursor()
    
    # First check if we already have this sackmann_id mapped
    c.execute("SELECT player_id FROM sackmann_player_map WHERE sackmann_id = ?", (sackmann_id,))
    row = c.fetchone()
    if row:
        return row['player_id'], 'cached'
    
    # Try exact name match
    c.execute("SELECT player_id, name FROM players WHERE LOWER(name) = LOWER(?)", (sackmann_name,))
    row = c.fetchone()
    if row:
        return row['player_id'], 'exact'
    
    # Try fuzzy matching on all players (with country filter if available)
    if country:
        c.execute("SELECT player_id, name FROM players WHERE country = ?", (country,))
    else:
        c.execute("SELECT player_id, name FROM players")
    
    best_match = None
    best_score = 0.85  # Minimum threshold
    
    for row in c.fetchall():
        score = fuzzy_match_score(sackmann_name, row['name'])
        if score > best_score:
            best_score = score
            best_match = row['player_id']
    
    if best_match:
        return best_match, 'fuzzy'
    
    return None, None


def create_sackmann_player(conn, sackmann_id, name, country=None, hand=None, birth_date=None):
    """Create a new player from Sackmann data."""
    # Generate a unique player_id for Sackmann players
    player_id = f"sackmann_{sackmann_id}"
    
    player_data = {
        'player_id': player_id,
        'name': name,
        'country': country,
        'source': 'sackmann',
    }
    
    # Add optional fields if available
    if birth_date:
        try:
            # Sackmann uses YYYYMMDD format
            dt = datetime.strptime(str(birth_date), '%Y%m%d')
            player_data['birth_date'] = dt.strftime('%Y-%m-%d')
        except:
            pass
    
    try:
        tennis_db.save_player(conn, player_data)
    except Exception as e:
        print(f"  Warning: Could not create player {name}: {e}")
    
    return player_id


def get_or_create_player(conn, sackmann_id, name, country=None, hand=None, birth_date=None):
    """Get existing player or create new one, and update mapping."""
    c = conn.cursor()
    
    player_id, match_type = find_matching_player(conn, name, sackmann_id, country)
    
    if player_id is None:
        # Create new player
        player_id = create_sackmann_player(conn, sackmann_id, name, country, hand, birth_date)
        match_type = 'created'
    
    # Save mapping
    try:
        c.execute("""
            INSERT OR REPLACE INTO sackmann_player_map (sackmann_id, player_id, player_name, matched_by, country)
            VALUES (?, ?, ?, ?, ?)
        """, (sackmann_id, player_id, name, match_type, country))
        conn.commit()
    except Exception as e:
        print(f"  Warning: Could not save mapping for {name}: {e}")
    
    return player_id


def parse_int(value):
    """Safely parse an integer value."""
    if value is None or value == '':
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def parse_date(date_str):
    """Parse Sackmann date format (YYYYMMDD) to ISO format."""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(str(date_str), '%Y%m%d')
        return dt.strftime('%Y-%m-%d')
    except:
        return None


def import_csv_data(conn, csv_content, source_name, dry_run=False, update_stats=False):
    """Import matches from CSV content."""
    reader = csv.DictReader(io.StringIO(csv_content))
    
    imported = 0
    updated = 0
    skipped = 0
    errors = 0
    
    c = conn.cursor()
    
    for row in reader:
        try:
            # Generate unique match_id
            tourney_id = row.get('tourney_id', '')
            match_num = row.get('match_num', '')
            match_id = f"sackmann_{tourney_id}_{match_num}"
            
            # Check if match already exists
            c.execute("SELECT w_ace FROM matches WHERE match_id = ?", (match_id,))
            existing = c.fetchone()
            
            should_update = False
            if existing:
                if update_stats and existing['w_ace'] is None:
                    should_update = True
                else:
                    skipped += 1
                    continue
            
            # Get or create winner
            winner_id = get_or_create_player(
                conn,
                row.get('winner_id'),
                row.get('winner_name'),
                row.get('winner_ioc'),
                row.get('winner_hand'),
                None  # birth date not directly available
            )
            
            # Get or create loser
            loser_id = get_or_create_player(
                conn,
                row.get('loser_id'),
                row.get('loser_name'),
                row.get('loser_ioc'),
                row.get('loser_hand'),
                None
            )
            
            if dry_run:
                imported += 1
                continue
            
            # Build match data
            match_data = {
                'match_id': match_id,
                'date': parse_date(row.get('tourney_date')),
                'winner_id': winner_id,
                'loser_id': loser_id,
                'score': row.get('score'),
                'tournament': row.get('tourney_name'),
                'round': row.get('round'),
                'source': source_name,
                'surface': row.get('surface'),
                'best_of': parse_int(row.get('best_of')),
                'minutes': parse_int(row.get('minutes')),
                'tourney_level': row.get('tourney_level'),
            }
            
            # Add stats columns
            for col in STATS_COLS:
                match_data[col] = parse_int(row.get(col))
            
            if should_update:
                set_clause = ", ".join([f"{k} = ?" for k in match_data.keys() if k != 'match_id'])
                params = [v for k, v in match_data.items() if k != 'match_id']
                params.append(match_id)
                c.execute(f"UPDATE matches SET {set_clause} WHERE match_id = ?", params)
                updated += 1
            else:
                # Insert match
                cols = ', '.join(match_data.keys())
                placeholders = ', '.join(['?' for _ in match_data])
                c.execute(f"INSERT INTO matches ({cols}) VALUES ({placeholders})", list(match_data.values()))
                imported += 1
            
            # Commit every 100 matches
            if (imported + updated) % 100 == 0:
                conn.commit()
                print(f"    Progress: {imported + updated} matches processed...")
        
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  Error processing match: {e}")
    
    conn.commit()
    return imported, updated, skipped, errors


    total_imported = 0
    total_updated = 0
    total_skipped = 0
    total_errors = 0
    
    for year in range(start_year, end_year + 1):
        filename = pattern.format(year=year)
        url = f"{base_url}/{filename}"
        
        print(f"\nProcessing {tour} {year}...")
        print(f"  URL: {url}")
        
        csv_content = download_csv(url)
        if csv_content is None:
            print(f"  Skipping {year} - file not found")
            continue
        
        imported, updated, skipped, errors = import_csv_data(conn, csv_content, f"sackmann-{tour}", dry_run, update_stats)
        
        print(f"  Imported: {imported}, Updated: {updated}, Skipped: {skipped}, Errors: {errors}")
        
        total_imported += imported
        total_updated += updated
        total_skipped += skipped
        total_errors += errors
    
    return total_imported, total_updated, total_skipped, total_errors


def main():
    parser = argparse.ArgumentParser(description="Import Jeff Sackmann tennis data")
    parser.add_argument('--tour', required=True, 
                        choices=['atp', 'wta', 'atp-challengers', 'wta-challengers', 'atp-futures', 'all'],
                        help='Tour to import')
    parser.add_argument('--start', type=int, required=True, help='Start year')
    parser.add_argument('--end', type=int, required=True, help='End year')
    parser.add_argument('--dry-run', action='store_true', help='Preview without importing')
    parser.add_argument('--update-stats', action='store_true', help='Update stats for existing matches if NULL')
    
    args = parser.parse_args()
    
    # Initialize database
    tennis_db.init_db()
    
    conn = get_db_connection()
    
    print(f"{'[DRY RUN] ' if args.dry_run else ''}Importing Sackmann data...")
    print(f"Tour: {args.tour}, Years: {args.start}-{args.end}, Update Stats: {args.update_stats}")
    
    if args.tour == 'all':
        tours = ['atp', 'wta', 'atp-challengers', 'wta-challengers', 'atp-futures']
    else:
        tours = [args.tour]
    
    grand_total = {'imported': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
    
    for tour in tours:
        print(f"\n{'='*60}")
        print(f"IMPORTING: {tour.upper()}")
        print('='*60)
        
        imported, updated, skipped, errors = import_tour(conn, tour, args.start, args.end, args.dry_run, args.update_stats)
        
        grand_total['imported'] += imported
        grand_total['updated'] += updated
        grand_total['skipped'] += skipped
        grand_total['errors'] += errors
    
    conn.close()
    
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print('='*60)
    print(f"Total Imported: {grand_total['imported']}")
    print(f"Total Updated: {grand_total['updated']}")
    print(f"Total Skipped (duplicates): {grand_total['skipped']}")
    print(f"Total Errors: {grand_total['errors']}")
    
    if args.dry_run:
        print("\n[DRY RUN] No data was actually imported.")


if __name__ == '__main__':
    main()
