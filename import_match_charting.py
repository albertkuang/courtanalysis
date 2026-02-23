#!/usr/bin/env python3
"""
Import Match Charting Project data from Jeff Sackmann's GitHub into the database.

This script imports:
1. Match metadata (players, tournament, date, etc.)
2. Aggregated player stats from Overview CSV
3. Point-by-point data (optional - very large)

Usage:
    python import_match_charting.py --tour atp --type matches
    python import_match_charting.py --tour wta --type matches
    python import_match_charting.py --tour atp --type overview
    python import_match_charting.py --tour wta --type overview
    python import_match_charting.py --tour atp --type all
    python import_match_charting.py --tour wta --type all
"""

import argparse
import csv
import io
import sqlite3
import requests
import os
from datetime import datetime
import tennis_db


# GitHub raw URLs
MCP_BASE = "https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master"

FILE_PATTERNS = {
    'atp': {
        'matches': 'charting-m-matches.csv',
        'overview': 'charting-m-stats-Overview.csv',
        'points': 'charting-m-points-2020s.csv',
    },
    'wta': {
        'matches': 'charting-w-matches.csv',
        'overview': 'charting-w-stats-Overview.csv',
        'points': 'charting-w-points-2020s.csv',
    }
}


def get_db_connection():
    """Get database connection."""
    conn = sqlite3.connect(tennis_db.DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_charting_tables(conn):
    """Create tables for match charting data."""
    c = conn.cursor()
    
    # Charted matches table
    c.execute('''
        CREATE TABLE IF NOT EXISTS charted_matches (
            match_id TEXT PRIMARY KEY,
            player1 TEXT,
            player2 TEXT,
            player1_hand TEXT,
            player2_hand TEXT,
            date TEXT,
            tournament TEXT,
            round TEXT,
            score TEXT,
            winner TEXT,
            loser TEXT,
            finish TEXT,
            total_games INTEGER,
            surface TEXT,
            num_sets INTEGER,
            tiebreaks INTEGER,
            service_games INTEGER,
            return_games INTEGER,
            total_points INTEGER,
            charted_by TEXT,
            tour TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Charted match points table (optional - can be very large)
    c.execute('''
        CREATE TABLE IF NOT EXISTS charted_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT,
            point_num INTEGER,
            set1 INTEGER,
            set2 INTEGER,
            game1 INTEGER,
            game2 INTEGER,
            points TEXT,
            game_winner TEXT,
            set_winner TEXT,
            set_loser TEXT,
            server INTEGER,
            receiver INTEGER,
            serve_result TEXT,
            return_result TEXT,
            rally_length INTEGER,
            winner TEXT,
            error TEXT,
            first_in TEXT,
            first_out TEXT,
            second_out TEXT,
            distance TEXT,
            run TEXT,
            notes TEXT,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Player charting overview stats
    c.execute('''
        CREATE TABLE IF NOT EXISTS player_charting_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT,
            match_count INTEGER,
            aces INTEGER,
            double_faults INTEGER,
            first_serve_in INTEGER,
            first_serve_total INTEGER,
            first_serve_won INTEGER,
            second_serve_won INTEGER,
            break_points_saved INTEGER,
            break_points_faced INTEGER,
            service_games_won INTEGER,
            service_games_total INTEGER,
            return_points_won INTEGER,
            return_points_total INTEGER,
            winners INTEGER,
            unforced_errors INTEGER,
            tour TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(player_name, tour)
        )
    ''')
    
    # Create indexes
    c.execute('CREATE INDEX IF NOT EXISTS idx_charted_points_match ON charted_points(match_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_charted_matches_player1 ON charted_matches(player1)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_charted_matches_player2 ON charted_matches(player2)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_charted_matches_date ON charted_matches(date)')
    
    conn.commit()
    print("Charting tables initialized.")


def download_csv(url, timeout=120):
    """Download a CSV file and return its content as list of dicts."""
    try:
        print(f"Downloading: {url}")
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        
        # Parse CSV into list of dicts
        lines = resp.text.strip().split('\n')
        if not lines:
            return []
        
        # Parse header
        reader = csv.reader(io.StringIO(resp.text))
        header = next(reader)
        
        # Parse rows
        rows = []
        for row in reader:
            if len(row) == len(header):
                rows.append(dict(zip(header, row)))
            else:
                # Handle mismatched columns - create dict with available fields
                row_dict = {}
                for i, val in enumerate(row):
                    if i < len(header):
                        row_dict[header[i]] = val
                rows.append(row_dict)
        
        return rows
    except requests.RequestException as e:
        print(f"Failed to download {url}: {e}")
        return []


def import_matches(conn, tour='atp'):
    """Import charted matches metadata."""
    print(f"\n=== Importing {tour.upper()} charted matches ===")
    
    url = f"{MCP_BASE}/{FILE_PATTERNS[tour]['matches']}"
    rows = download_csv(url)
    if not rows:
        return 0
    
    c = conn.cursor()
    count = 0
    
    for row in rows:
        try:
            c.execute('''
                INSERT OR REPLACE INTO charted_matches (
                    match_id, player1, player2, player1_hand, player2_hand,
                    date, tournament, round, score, winner, loser,
                    finish, total_games, surface, num_sets, tiebreaks,
                    service_games, return_games, total_points, charted_by, tour
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row.get('matchId'),
                row.get('player1'),
                row.get('player2'),
                row.get('player1Hand'),
                row.get('player2Hand'),
                row.get('date'),
                row.get('tournament'),
                row.get('round'),
                row.get('score'),
                row.get('winner'),
                row.get('loser'),
                row.get('finish'),
                int(row.get('totalGames', 0)) if row.get('totalGames') and row.get('totalGames').isdigit() else None,
                row.get('surface'),
                int(row.get('numSets', 0)) if row.get('numSets') and row.get('numSets').isdigit() else None,
                int(row.get('tiebreaks', 0)) if row.get('tiebreaks') and row.get('tiebreaks').isdigit() else None,
                int(row.get('serviceGames', 0)) if row.get('serviceGames') and row.get('serviceGames').isdigit() else None,
                int(row.get('returnGames', 0)) if row.get('returnGames') and row.get('returnGames').isdigit() else None,
                int(row.get('totalPoints', 0)) if row.get('totalPoints') and row.get('totalPoints').isdigit() else None,
                row.get('chartedBy'),
                tour.upper()
            ))
            count += 1
        except Exception as e:
            # Skip problematic rows
            continue
    
    conn.commit()
    print(f"Imported {count} charted matches for {tour.upper()}")
    return count


def import_overview_stats(conn, tour='atp'):
    """Import player charting overview stats."""
    print(f"\n=== Importing {tour.upper()} player charting stats ===")
    
    url = f"{MCP_BASE}/{FILE_PATTERNS[tour]['overview']}"
    rows = download_csv(url)
    if not rows:
        return 0
    
    c = conn.cursor()
    count = 0
    
    for row in rows:
        try:
            c.execute('''
                INSERT OR REPLACE INTO player_charting_stats (
                    player_name, match_count, aces, double_faults,
                    first_serve_in, first_serve_total, first_serve_won,
                    second_serve_won, break_points_saved, break_points_faced,
                    service_games_won, service_games_total,
                    return_points_won, return_points_total,
                    winners, unforced_errors, tour, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                row.get('player_name'),
                int(row.get('matches', 0)) if row.get('matches') and row.get('matches').isdigit() else 0,
                int(row.get('ace', 0)) if row.get('ace') and row.get('ace').isdigit() else 0,
                int(row.get('df', 0)) if row.get('df') and row.get('df').isdigit() else 0,
                int(row.get('firstIn', 0)) if row.get('firstIn') and row.get('firstIn').isdigit() else 0,
                int(row.get('firstTotal', 0)) if row.get('firstTotal') and row.get('firstTotal').isdigit() else 0,
                int(row.get('firstWon', 0)) if row.get('firstWon') and row.get('firstWon').isdigit() else 0,
                int(row.get('secondWon', 0)) if row.get('secondWon') and row.get('secondWon').isdigit() else 0,
                int(row.get('bpSaved', 0)) if row.get('bpSaved') and row.get('bpSaved').isdigit() else 0,
                int(row.get('bpFaced', 0)) if row.get('bpFaced') and row.get('bpFaced').isdigit() else 0,
                int(row.get('svGmsWon', 0)) if row.get('svGmsWon') and row.get('svGmsWon').isdigit() else 0,
                int(row.get('svGmsTotal', 0)) if row.get('svGmsTotal') and row.get('svGmsTotal').isdigit() else 0,
                int(row.get('retPointsWon', 0)) if row.get('retPointsWon') and row.get('retPointsWon').isdigit() else 0,
                int(row.get('retPointsTotal', 0)) if row.get('retPointsTotal') and row.get('retPointsTotal').isdigit() else 0,
                int(row.get('winner', 0)) if row.get('winner') and row.get('winner').isdigit() else 0,
                int(row.get('unforced', 0)) if row.get('unforced') and row.get('unforced').isdigit() else 0,
                tour.upper()
            ))
            count += 1
        except Exception as e:
            continue
    
    conn.commit()
    print(f"Imported {count} player charting stats for {tour.upper()}")
    return count


def import_points(conn, tour='atp', limit=None):
    """Import point-by-point data (can be large)."""
    print(f"\n=== Importing {tour.upper()} point data ===")
    print("WARNING: This can take a while and uses significant disk space.")
    
    url = f"{MCP_BASE}/{FILE_PATTERNS[tour]['points']}"
    content = download_csv(url, timeout=300)
    if not content:
        return 0
    
    c = conn.cursor()
    count = 0
    
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        try:
            c.execute('''
                INSERT INTO charted_points (
                    match_id, point_num, set1, set2, game1, game2,
                    points, game_winner, set_winner, set_loser,
                    server, receiver, serve_result, return_result,
                    rally_length, winner, error, first_in, first_out,
                    second_out, distance, run, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row.get('matchId'),
                int(row.get('Pt', 0)) if row.get('Pt') else None,
                int(row.get('Set1', 0)) if row.get('Set1') else None,
                int(row.get('Set2', 0)) if row.get('Set2') else None,
                int(row.get('Gm1', 0)) if row.get('Gm1') else None,
                int(row.get('Gm2', 0)) if row.get('Gm2') else None,
                row.get('Pts'),
                row.get('GmW'),
                row.get('SetW'),
                row.get('SetL'),
                int(row.get('Server', 0)) if row.get('Server') else None,
                int(row.get('Rcv', 0)) if row.get('Rcv') else None,
                row.get('Svr'),
                row.get('Ret'),
                int(row.get('RalLen', 0)) if row.get('RalLen') else None,
                row.get('Winner'),
                row.get('Err'),
                row.get('1stIn'),
                row.get('1stOut'),
                row.get('2ndOut'),
                row.get('Distance'),
                row.get('Run'),
                row.get('note')
            ))
            count += 1
            
            if limit and count >= limit:
                print(f"Reached limit of {limit} points")
                break
                
            if count % 10000 == 0:
                print(f"  Imported {count} points...")
                
        except Exception as e:
            continue
    
    conn.commit()
    print(f"Imported {count} points for {tour.upper()}")
    return count


def show_stats(conn):
    """Show import statistics."""
    c = conn.cursor()
    
    print("\n=== Match Charting Import Stats ===")
    
    try:
        c.execute("SELECT tour, COUNT(*) as count FROM charted_matches GROUP BY tour")
        for row in c.fetchall():
            print(f"  Charted matches ({row['tour']}): {row['count']:,}")
    except:
        print("  No matches data")
    
    try:
        c.execute("SELECT tour, COUNT(*) as count FROM player_charting_stats GROUP BY tour")
        for row in c.fetchall():
            print(f"  Player stats ({row['tour']}): {row['count']:,}")
    except:
        print("  No player stats data")
    
    try:
        c.execute("SELECT COUNT(*) as count FROM charted_points")
        row = c.fetchone()
        print(f"  Points: {row['count']:,}")
    except:
        print("  No points data")


def main():
    parser = argparse.ArgumentParser(description='Import Match Charting Project data')
    parser.add_argument('--tour', choices=['atp', 'wta', 'all'], default='all',
                        help='Tour to import (atp, wta, or all)')
    parser.add_argument('--type', choices=['matches', 'overview', 'points', 'all'], 
                        default='all', help='Type of data to import')
    parser.add_argument('--limit-points', type=int, default=None,
                        help='Limit number of points to import (for testing)')
    
    args = parser.parse_args()
    
    conn = get_db_connection()
    
    # Initialize tables
    init_charting_tables(conn)
    
    tours = ['atp', 'wta'] if args.tour == 'all' else [args.tour]
    
    for tour in tours:
        if args.type in ['matches', 'all']:
            import_matches(conn, tour)
        
        if args.type in ['overview', 'all']:
            import_overview_stats(conn, tour)
        
        if args.type in ['points', 'all']:
            import_points(conn, tour, limit=args.limit_points)
    
    # Show final stats
    show_stats(conn)
    
    conn.close()
    print("\nImport complete!")


if __name__ == "__main__":
    main()
