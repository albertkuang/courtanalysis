"""
Import ATP/WTA ranking data from Jeff Sackmann's GitHub repositories.
Downloads and imports rankings from 2025+ to fill in recent data gaps.
"""
import sqlite3
import requests
import csv
from io import StringIO
from datetime import datetime

# Base URLs for ranking files
ATP_RANKINGS_URL = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_rankings_current.csv"
WTA_RANKINGS_URL = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_rankings_current.csv"

# Also try historical files for 2020s decade
ATP_RANKINGS_20S_URL = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_rankings_20s.csv"
WTA_RANKINGS_20S_URL = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_rankings_20s.csv"

def get_db_connection():
    conn = sqlite3.connect('tennis_data.db')
    conn.row_factory = sqlite3.Row
    return conn

def download_csv(url):
    """Download a CSV file from URL and return as list of dicts."""
    print(f"Downloading: {url}")
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        content = response.text
        reader = csv.DictReader(StringIO(content))
        return list(reader)
    except Exception as e:
        print(f"  Error downloading: {e}")
        return []

def parse_date(date_str):
    """Convert date from YYYYMMDD to YYYY-MM-DD format."""
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str

def import_rankings(conn, rows, tour_prefix, min_date=None):
    """Import ranking rows into the database."""
    c = conn.cursor()
    
    # Get existing dates to avoid re-importing
    c.execute("SELECT DISTINCT date FROM rankings WHERE player_id LIKE ?", (f"{tour_prefix}_%",))
    existing_dates = set(r[0] for r in c.fetchall())
    
    imported = 0
    skipped_date = 0
    skipped_old = 0
    
    for row in rows:
        # Parse the row
        try:
            ranking_date_raw = row.get('ranking_date', '')
            ranking_date = parse_date(ranking_date_raw)
            
            # Skip if older than min_date
            if min_date and ranking_date < min_date:
                skipped_old += 1
                continue
            
            # Skip if date already exists
            if ranking_date in existing_dates:
                skipped_date += 1
                continue
            
            player_id = f"{tour_prefix}_{row.get('player', '')}"
            rank = int(row.get('rank', 0))
            points = int(row.get('points', 0))
            tours = int(row.get('tours', 0) or 0)
            
            # Create unique rank_id
            rank_id = f"{ranking_date_raw}_{player_id}"
            
            # Insert (ignore duplicates)
            c.execute("""
                INSERT OR IGNORE INTO rankings (rank_id, date, player_id, rank, points, tours)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (rank_id, ranking_date, player_id, rank, points, tours))
            
            if c.rowcount > 0:
                imported += 1
                
        except Exception as e:
            print(f"  Error parsing row: {e} - {row}")
    
    conn.commit()
    print(f"  Imported: {imported}, Skipped (existing): {skipped_date}, Skipped (too old): {skipped_old}")
    return imported

def main():
    print("=" * 60)
    print("Importing ATP/WTA Ranking Data (2025+)")
    print("=" * 60)
    
    conn = get_db_connection()
    
    # Check current latest date
    c = conn.cursor()
    c.execute("SELECT MAX(date) FROM rankings")
    latest = c.fetchone()[0]
    print(f"\nCurrent latest ranking date in DB: {latest}")
    
    # We want to import data from 2025-01-01 onwards
    min_date = "2025-01-01"
    print(f"Importing rankings from: {min_date}")
    
    total_imported = 0
    
    # Try ATP 20s file (covers 2020-present)
    print("\n[1/4] Downloading ATP rankings (2020s)...")
    atp_20s = download_csv(ATP_RANKINGS_20S_URL)
    if atp_20s:
        imported = import_rankings(conn, atp_20s, "atp", min_date)
        total_imported += imported
    
    # Try ATP current file
    print("\n[2/4] Downloading ATP current rankings...")
    atp_current = download_csv(ATP_RANKINGS_URL)
    if atp_current:
        imported = import_rankings(conn, atp_current, "atp", min_date)
        total_imported += imported
    
    # Try WTA 20s file
    print("\n[3/4] Downloading WTA rankings (2020s)...")
    wta_20s = download_csv(WTA_RANKINGS_20S_URL)
    if wta_20s:
        imported = import_rankings(conn, wta_20s, "wta", min_date)
        total_imported += imported
    
    # Try WTA current file
    print("\n[4/4] Downloading WTA current rankings...")
    wta_current = download_csv(WTA_RANKINGS_URL)
    if wta_current:
        imported = import_rankings(conn, wta_current, "wta", min_date)
        total_imported += imported
    
    # Final stats
    c.execute("SELECT MIN(date), MAX(date), COUNT(*) FROM rankings")
    stats = c.fetchone()
    
    print("\n" + "=" * 60)
    print(f"IMPORT COMPLETE")
    print(f"Total new rankings imported: {total_imported}")
    print(f"Rankings table now spans: {stats[0]} to {stats[1]}")
    print(f"Total ranking entries: {stats[2]:,}")
    print("=" * 60)
    
    conn.close()

if __name__ == "__main__":
    main()
