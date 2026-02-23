#!/usr/bin/env python3
"""
Backfill missing match statistics from Jeff Sackmann's tennis data into the local database.
"""

import sqlite3
import csv
import io
import requests
import argparse
from datetime import datetime
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

META_COLS = ['surface', 'best_of', 'minutes', 'tourney_level']

def get_db_connection():
    conn = sqlite3.connect(tennis_db.DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def download_csv(url):
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"  Failed to download {url}: {e}")
        return None

def parse_int(value):
    if value is None or value == '':
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None

def backfill_tour_year(conn, tour, year, dry_run=False):
    if tour not in FILE_PATTERNS:
        print(f"Unknown tour: {tour}")
        return
    
    base_url, pattern = FILE_PATTERNS[tour]
    filename = pattern.format(year=year)
    url = f"{base_url}/{filename}"
    source_name = f"sackmann-{tour}"
    
    print(f"\nScanning database for {source_name} matches in {year} needing stats...")
    
    c = conn.cursor()
    # Find matches from this source and year that have NULL stats
    # We estimate year by the date in the database
    c.execute("""
        SELECT match_id FROM matches 
        WHERE source = ? 
        AND date LIKE ? 
        AND w_ace IS NULL
    """, (source_name, f"{year}-%"))
    
    matches_to_update = {row['match_id'] for row in c.fetchall()}
    
    if not matches_to_update:
        print(f"  No matches needing backfill for {source_name} {year}")
        return 0
    
    print(f"  Found {len(matches_to_update)} matches needing statistics.")
    
    csv_content = download_csv(url)
    if csv_content is None:
        return 0
    
    reader = csv.DictReader(io.StringIO(csv_content))
    updated_count = 0
    
    for row in reader:
        tourney_id = row.get('tourney_id', '')
        match_num = row.get('match_num', '')
        match_id = f"sackmann_{tourney_id}_{match_num}"
        
        if match_id in matches_to_update:
            if dry_run:
                updated_count += 1
                continue
            
            # Prepare update data
            update_data = {}
            for col in STATS_COLS:
                val = parse_int(row.get(col))
                if val is not None:
                    update_data[col] = val
            
            for col in META_COLS:
                val = row.get(col)
                if col in ['best_of', 'minutes']:
                    val = parse_int(val)
                if val:
                    update_data[col] = val
            
            if not update_data:
                continue
                
            # Execute update
            set_clause = ", ".join([f"{k} = ?" for k in update_data.keys()])
            params = list(update_data.values())
            params.append(match_id)
            
            c.execute(f"UPDATE matches SET {set_clause} WHERE match_id = ?", params)
            updated_count += 1
            
            if updated_count % 100 == 0:
                conn.commit()
                print(f"    Updated {updated_count} matches...")
                
    conn.commit()
    print(f"  Successfully updated {updated_count} matches for {source_name} {year}")
    return updated_count

def main():
    parser = argparse.ArgumentParser(description="Backfill missing tennis match statistics")
    parser.add_argument('--tour', choices=['atp', 'wta', 'atp-challengers', 'wta-challengers', 'atp-futures', 'all'], default='all')
    parser.add_argument('--start', type=int, default=2020)
    parser.add_argument('--end', type=int, default=2024)
    parser.add_argument('--dry-run', action='store_true')
    
    args = parser.parse_args()
    
    conn = get_db_connection()
    
    if args.tour == 'all':
        tours = ['atp', 'wta', 'atp-challengers', 'wta-challengers', 'atp-futures']
    else:
        tours = [args.tour]
        
    total_updated = 0
    for tour in tours:
        for year in range(args.start, args.end + 1):
            total_updated += backfill_tour_year(conn, tour, year, args.dry_run)
            
    conn.close()
    print(f"\nDone. Total matches updated: {total_updated}")

if __name__ == "__main__":
    main()
