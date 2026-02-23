#!/usr/bin/env python3
"""
Import Grand Slam point-by-point data from Jeff Sackmann's tennis_slam_pointbypoint.

This imports:
1. Slam matches (match metadata)
2. Slam points (point-by-point data)

Source: https://github.com/JeffSackmann/tennis_slam_pointbypoint

Usage:
    python import_slam_data.py --tour usopen --year 2024 --type matches
    python import_slam_data.py --tour usopen --year 2024 --type points
    python import_slam_data.py --tour all --year 2024 --type all
    python import_slam_data.py --tour usopen --year all --type matches
"""

import argparse
import csv
import io
import sqlite3
import requests
import os
import re
from datetime import datetime
import tennis_db


# GitHub raw URLs
ATP_BASE = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master"
WTA_BASE = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master"
PBP_BASE = "https://raw.githubusercontent.com/JeffSackmann/tennis_slam_pointbypoint/master"

# Tournament name mapping from Sackmann's names to our display names
SACKMANN_TO_OURS = {
    'Australian Open': 'Australian Open',
    'Roland Garros': 'French Open',
    'Wimbledon': 'Wimbledon',
    'Us Open': 'US Open',
    'US Open': 'US Open',
}

# Tournament display names
DISPLAY_NAMES = {
    'ausopen': 'Australian Open',
    'frenchopen': 'French Open',
    'wimbledon': 'Wimbledon',
    'usopen': 'US Open'
}

# ID mapping for tours
TOUR_TO_ID = {
    'ausopen': 'ausopen',
    'australianopen': 'ausopen',
    'frenchopen': 'frenchopen',
    'wimbledon': 'wimbledon',
    'usopen': 'usopen'
}

# Inverse mapping for internal tour keys to Sackmann filenames
TOUR_TO_FILENAME = {
    'ausopen': 'ausopen',
    'frenchopen': 'frenchopen',
    'wimbledon': 'wimbledon',
    'usopen': 'usopen'
}

# Years to import
YEARS = list(range(2011, 2026))


def get_db_connection():
    """Get database connection."""
    conn = sqlite3.connect(tennis_db.DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_slam_tables(conn, drop=False):
    """Create tables for Grand Slam data."""
    c = conn.cursor()
    
    if drop:
        print("Dropping existing slam tables...")
        c.execute('DROP TABLE IF EXISTS slam_matches')
        c.execute('DROP TABLE IF EXISTS slam_points')
    
    # Slam matches table
    c.execute('''
        CREATE TABLE IF NOT EXISTS slam_matches (
            match_id TEXT PRIMARY KEY,
            year INTEGER,
            tournament TEXT,
            round TEXT,
            winner_name TEXT,
            loser_name TEXT,
            winner_seed INTEGER,
            loser_seed INTEGER,
            winner_rank INTEGER,
            loser_rank INTEGER,
            score TEXT,
            best_of INTEGER,
            match_duration INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Slam points table - UPDATED schema to match PBP repo
    c.execute('''
        CREATE TABLE IF NOT EXISTS slam_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT,
            point_num INTEGER,
            set_num INTEGER,
            game_num INTEGER,
            p1_games INTEGER,
            p2_games INTEGER,
            point_server INTEGER,
            server_score TEXT,
            receiver_score TEXT,
            winner_of_point TEXT,  -- 'S' for server, 'R' for receiver
            serve_num INTEGER,
            serve_width TEXT,
            serve_depth TEXT,
            return_depth TEXT,
            rally_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes
    c.execute('CREATE INDEX IF NOT EXISTS idx_slam_points_match ON slam_points(match_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_slam_matches_year ON slam_matches(year)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_slam_matches_tournament ON slam_matches(tournament)')
    
    conn.commit()
    print("Slam tables initialized.")


def download_csv(url):
    """Download a CSV file and return list of dicts."""
    try:
        print(f"  Downloading: {url}")
        resp = requests.get(url, timeout=60)
        if resp.status_code != 200:
            print(f"    Not found ({resp.status_code})")
            return []
        
        # Use csv.DictReader for more robust header handling
        content = resp.text
        # Remove BOM if present
        if content.startswith('\ufeff'):
            content = content[1:]
            
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        print(f"    Downloaded {len(rows)} rows")
        return rows
    except Exception as e:
        print(f"    Error: {e}")
        return []


def import_matches(conn, tour, year):
    """Import slam match metadata, merging PBP IDs with ATP/WTA results."""
    print(f"\n=== Importing {tour.upper()} {year} match metadata ===")
    
    tours_to_process = [tour] if tour != 'all' else ['ausopen', 'frenchopen', 'wimbledon', 'usopen']
    years_to_process = [year] if year != 'all' else YEARS
    
    total_imported = 0
    c = conn.cursor()
    
    for y in years_to_process:
        # Load ATP/WTA results for enrichment once per year
        results_by_names = {}
        for gender, base_url in [('atp', ATP_BASE), ('wta', WTA_BASE)]:
            url = f"{base_url}/{gender}_matches_{y}.csv"
            res_rows = download_csv(url)
            for r in res_rows:
                tourney_name = r.get('tourney_name', '')
                if tourney_name in SACKMANN_TO_OURS:
                    # Create a key using sorted player names for matching
                    # Normalize names: strip, lowercase, remove apostrophes
                    p1 = r.get('winner_name', '').strip().lower().replace("'", "").replace("-", " ")
                    p2 = r.get('loser_name', '').strip().lower().replace("'", "").replace("-", " ")
                    if p1 and p2:
                        name_key = tuple(sorted([p1, p2]))
                        results_by_names[name_key] = r

        for t in tours_to_process:
            # Download PBP matches for the actual IDs
            pbp_url = f"{PBP_BASE}/{y}-{t}-matches.csv"
            pbp_rows = download_csv(pbp_url)
            if not pbp_rows:
                continue
                
            for row in pbp_rows:
                match_id = row.get('match_id')
                p1_name = row.get('player1', '').strip()
                p2_name = row.get('player2', '').strip()
                
                if not p1_name or not p2_name:
                    continue
                
                # Try to find match in results with normalized names
                n1 = p1_name.lower().replace("'", "").replace("-", " ")
                n2 = p2_name.lower().replace("'", "").replace("-", " ")
                name_key = tuple(sorted([n1, n2]))
                res = results_by_names.get(name_key)
                
                if res:
                    winner_name = res.get('winner_name')
                    loser_name = res.get('loser_name')
                    winner_seed = res.get('winner_seed')
                    loser_seed = res.get('loser_seed')
                    winner_rank = res.get('winner_rank')
                    loser_rank = res.get('loser_rank')
                    score = res.get('score')
                    best_of = res.get('best_of')
                    duration = res.get('minutes')
                    
                    # Round map
                    round_map = {'F': 'Final', 'SF': 'Semifinal', 'QF': 'Quarterfinal', 'R16': 'Round of 16', 
                               'R32': 'Round of 32', 'R64': 'Round of 64', 'R128': 'Round of 128'}
                    round_name = round_map.get(res.get('round', ''), res.get('round', ''))
                else:
                    # Fallback to PBP data if no match found in results
                    winner_name = p1_name
                    loser_name = p2_name
                    winner_seed = None
                    loser_seed = None
                    winner_rank = None
                    loser_rank = None
                    score = "TBD"
                    best_of = 5 if t != 'frenchopen' else 5 # GS is usually 5 for men, but PBP often has both
                    duration = None
                    round_name = row.get('round', '')

                try:
                    display_tournament = SACKMANN_TO_OURS.get(res.get('tourney_name')) if res else DISPLAY_NAMES.get(t, t.upper())
                    
                    c.execute('''
                        INSERT OR REPLACE INTO slam_matches (
                            match_id, year, tournament, round,
                            winner_name, loser_name,
                            winner_seed, loser_seed,
                            winner_rank, loser_rank,
                            score, best_of, match_duration
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        match_id,
                        y,
                        display_tournament,
                        round_name,
                        winner_name,
                        loser_name,
                        int(winner_seed) if winner_seed and str(winner_seed).isdigit() else None,
                        int(loser_seed) if loser_seed and str(loser_seed).isdigit() else None,
                        int(winner_rank) if winner_rank and str(winner_rank).isdigit() else None,
                        int(loser_rank) if loser_rank and str(loser_rank).isdigit() else None,
                        score,
                        int(best_of) if best_of and str(best_of).isdigit() else None,
                        int(duration) if duration and str(duration).isdigit() else None,
                    ))
                    total_imported += 1
                except Exception as e:
                    print(f"      Error inserting match {match_id}: {e}")
                    
        conn.commit()
    
    print(f"Total imported matches: {total_imported}")
    return total_imported


def import_points(conn, tour, year, limit=None):
    """Import slam point-by-point data from PBP repo."""
    print(f"\n=== Importing {tour.upper()} {year} point-by-point data ===")
    
    tours_to_process = [tour] if tour != 'all' else ['ausopen', 'frenchopen', 'wimbledon', 'usopen']
    years_to_process = [year] if year != 'all' else YEARS
    
    total_imported = 0
    c = conn.cursor()
    
    for y in years_to_process:
        for t in tours_to_process:
            # Filename in repo is like 2024-usopen-points.csv
            filename = f"{y}-{t}-points.csv"
            url = f"{PBP_BASE}/{filename}"
            rows = download_csv(url)
            if not rows:
                continue
            
            # Delete existing points for these matches to avoid duplicates
            # match_ids for this file start with {y}-{t}-
            match_id_prefix = f"{y}-{t}-%"
            c.execute("DELETE FROM slam_points WHERE match_id LIKE ?", (match_id_prefix,))
            
            for row in rows:
                try:
                    match_id = row.get('match_id')
                    p_winner = row.get('PointWinner')
                    p_server = row.get('PointServer')
                    
                    # Convert PointWinner/Server to 'S' (Server) or 'R' (Receiver)
                    # Frontend expects 'S' or 'R'
                    winner_of_point = 'S' if p_winner == p_server else 'R'
                    
                    c.execute('''
                        INSERT INTO slam_points (
                            match_id, point_num, set_num, game_num, 
                            p1_games, p2_games, point_server,
                            server_score, receiver_score, winner_of_point,
                            serve_num, serve_width, serve_depth, return_depth,
                            rally_count
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        match_id,
                        int(row.get('PointNumber')) if row.get('PointNumber') else None,
                        int(row.get('SetNo')) if row.get('SetNo') else None,
                        int(row.get('GameNo')) if row.get('GameNo') else None,
                        int(row.get('P1GamesWon')) if row.get('P1GamesWon') else 0,
                        int(row.get('P2GamesWon')) if row.get('P2GamesWon') else 0,
                        int(p_server) if p_server else None,
                        row.get('P1Score') if p_server == '1' else row.get('P2Score'),
                        row.get('P2Score') if p_server == '1' else row.get('P1Score'),
                        winner_of_point,
                        int(row.get('ServeNumber')) if row.get('ServeNumber') else None,
                        row.get('ServeWidth'),
                        row.get('ServeDepth'),
                        row.get('ReturnDepth'),
                        int(row.get('RallyCount')) if row.get('RallyCount') else 0,
                    ))
                    total_imported += 1
                    
                    if limit and total_imported >= limit:
                        break
                    if total_imported % 10000 == 0:
                        print(f"    Imported {total_imported} points...")
                        
                except Exception as e:
                    continue
            
            conn.commit()
            if limit and total_imported >= limit:
                break
                
    print(f"Total imported points: {total_imported}")
    return total_imported


def show_stats(conn):
    """Show import statistics."""
    c = conn.cursor()
    print("\n=== Grand Slam Import Stats ===")
    
    try:
        c.execute("SELECT tournament, year, COUNT(*) as count FROM slam_matches GROUP BY tournament, year ORDER BY year DESC")
        print("\nMatches by Tournament:")
        for row in c.fetchall():
            print(f"  {row['tournament']} {row['year']}: {row['count']:,} matches")
    except Exception as e:
        print(f"  Error: {e}")
    
    try:
        c.execute("SELECT COUNT(*) as count FROM slam_points")
        row = c.fetchone()
        print(f"\nTotal Points: {row['count']:,}")
    except Exception as e:
        print(f"  Error: {e}")


def main():
    parser = argparse.ArgumentParser(description='Import Grand Slam Point-by-Point data')
    parser.add_argument('--tour', choices=['ausopen', 'frenchopen', 'wimbledon', 'usopen', 'all'], 
                        default='all', help='Tournament')
    parser.add_argument('--year', default='2024', help='Year (or all)')
    parser.add_argument('--type', choices=['matches', 'points', 'all'], default='all',
                        help='Type of data to import')
    parser.add_argument('--limit-points', type=int, default=None,
                        help='Limit number of points to import (for testing)')
    parser.add_argument('--drop', action='store_true', help='Drop existing tables before import')
    
    args = parser.parse_args()
    
    # Convert year to int or keep as 'all'
    year = args.year
    if year != 'all':
        year = int(year)
    
    conn = get_db_connection()
    
    # Initialize tables
    init_slam_tables(conn, drop=args.drop)
    
    # Import data
    if args.type in ['matches', 'all']:
        import_matches(conn, args.tour, year)
    
    if args.type in ['points', 'all']:
        import_points(conn, args.tour, year, limit=args.limit_points)
    
    # Show stats
    show_stats(conn)
    
    conn.close()
    print("\nImport complete!")


if __name__ == "__main__":
    import argparse
    import csv
    import io
    import sqlite3
    import requests
    import os
    from datetime import datetime
    import tennis_db
    main()
