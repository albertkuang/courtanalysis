#!/usr/bin/env python3
"""
Phase 2: Bulk load all data from JSONL files into SQLite database.
Loads: Players, Matches, UTR History

Uses optimized batch inserts for 100x+ speedup over individual inserts.

Usage:
    python load_data_to_db.py --input-dir ./scrape_output/CAN_adult
    python load_data_to_db.py --input-dir ./scrape_output/CAN_junior --batch-size 5000
"""

import argparse
import json
import sqlite3
import sys
import os
from datetime import datetime

import tennis_db

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

DB_FILE = 'tennis_data.db'


def count_lines(filepath):
    """Count lines in file for progress tracking."""
    if not os.path.exists(filepath):
        return 0
    count = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        for _ in f:
            count += 1
    return count


def bulk_load_players(filepath, batch_size=200): # Reduced batch size due to more vars in query
    """
    Bulk load players from JSONL file.
    """
    if not os.path.exists(filepath):
        print(f"   ⚠ File not found: {filepath}")
        return 0
    
    print(f"\n📊 Loading Players...")
    total = count_lines(filepath)
    print(f"   Found {total:,} players in file")
    
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    
    now = datetime.now().isoformat()
    
    inserted = 0
    batch = []
    
    sql = """
    INSERT INTO players 
    (player_id, name, country, gender, age, birth_date, location, 
     utr_singles, utr_doubles, college, age_group, pro_rank, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(player_id) DO UPDATE SET
        name=excluded.name,
        country=excluded.country,
        gender=excluded.gender,
        age=excluded.age,
        birth_date=excluded.birth_date,
        location=excluded.location,
        utr_singles=excluded.utr_singles,
        utr_doubles=excluded.utr_doubles,
        college=excluded.college,
        age_group=excluded.age_group,
        pro_rank=excluded.pro_rank,
        updated_at=excluded.updated_at
    """
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                p = json.loads(line.strip())
                batch.append((
                    str(p.get('player_id', '')),
                    p.get('name'),
                    p.get('country'),
                    p.get('gender'),
                    p.get('age'),
                    p.get('birth_date'),
                    p.get('location'),
                    p.get('utr_singles'),
                    p.get('utr_doubles'),
                    p.get('college'),
                    p.get('age_group'),
                    p.get('pro_rank'),
                    now
                ))
                
                if len(batch) >= batch_size:
                    conn.executemany(sql, batch)
                    conn.commit()
                    inserted += len(batch)
                    batch.clear()
                    sys.stdout.write(f"\r   Inserted: {inserted:,}/{total:,}")
                    sys.stdout.flush()
            except:
                continue
    
    # Final batch
    if batch:
        conn.executemany(sql, batch)
        conn.commit()
        inserted += len(batch)
    
    conn.close()
    print(f"\r   ✓ Inserted {inserted:,} players")
    return inserted


def bulk_load_matches(filepath, batch_size=2000):
    """
    Bulk load matches from JSONL file.
    Also auto-creates any missing players.
    """
    if not os.path.exists(filepath):
        print(f"   ⚠ File not found: {filepath}")
        return 0
    
    print(f"\n🎯 Loading Matches...")
    total = count_lines(filepath)
    print(f"   Found {total:,} matches in file")
    
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA cache_size=10000')
    
    # Build player cache
    c = conn.cursor()
    c.execute("SELECT player_id FROM players")
    existing_players = set(str(row[0]) for row in c.fetchall())
    print(f"   {len(existing_players):,} players in cache")
    
    now = datetime.now().isoformat()
    
    match_sql = """
    INSERT OR IGNORE INTO matches 
    (match_id, date, winner_id, loser_id, score, tournament, round, source, winner_utr, loser_utr, processed_player_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    player_sql = "INSERT OR IGNORE INTO players (player_id, name, utr_singles, updated_at) VALUES (?, ?, ?, ?)"
    
    inserted = 0
    players_created = 0
    match_batch = []
    new_players = {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                m = json.loads(line.strip())
                
                winner_id = str(m.get('winner_id', ''))
                loser_id = str(m.get('loser_id', ''))
                
                # Track new players to create
                if winner_id and winner_id not in existing_players and winner_id not in new_players:
                    new_players[winner_id] = (m.get('winner_name', 'Unknown'), m.get('winner_utr'))
                if loser_id and loser_id not in existing_players and loser_id not in new_players:
                    new_players[loser_id] = (m.get('loser_name', 'Unknown'), m.get('loser_utr'))
                
                match_batch.append((
                    str(m.get('match_id', '')),
                    m.get('date'),
                    winner_id,
                    loser_id,
                    m.get('score', ''),
                    m.get('tournament', ''),
                    m.get('round', ''),
                    'UTR',
                    m.get('winner_utr'),
                    m.get('loser_utr'),
                    ''  # processed_player_id not needed
                ))
                
                if len(match_batch) >= batch_size:
                    # First create any new players
                    if new_players:
                        player_data = [(pid, data[0], data[1], now) for pid, data in new_players.items()]
                        conn.executemany(player_sql, player_data)
                        players_created += len(player_data)
                        for pid in new_players:
                            existing_players.add(pid)
                        new_players.clear()
                    
                    # Then insert matches
                    conn.executemany(match_sql, match_batch)
                    conn.commit()
                    inserted += len(match_batch)
                    match_batch.clear()
                    
                    pct = (inserted / total) * 100
                    sys.stdout.write(f"\r   [{pct:.0f}%] Inserted: {inserted:,}/{total:,} | New players: {players_created:,}")
                    sys.stdout.flush()
            except:
                continue
    
    # Final batch
    if new_players:
        player_data = [(pid, data[0], data[1], now) for pid, data in new_players.items()]
        conn.executemany(player_sql, player_data)
        players_created += len(player_data)
    
    if match_batch:
        conn.executemany(match_sql, match_batch)
        conn.commit()
        inserted += len(match_batch)
    
    conn.close()
    print(f"\r   ✓ Inserted {inserted:,} matches, created {players_created:,} new players")
    return inserted


def bulk_load_history(filepath, batch_size=5000):
    """
    Bulk load UTR history from JSONL file.
    """
    if not os.path.exists(filepath):
        print(f"   ⚠ File not found: {filepath}")
        return 0
    
    print(f"\n📈 Loading UTR History...")
    total = count_lines(filepath)
    print(f"   Found {total:,} history records in file")
    
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    
    sql = """
    INSERT OR IGNORE INTO utr_history (player_id, date, rating, type)
    VALUES (?, ?, ?, ?)
    """
    
    inserted = 0
    batch = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                h = json.loads(line.strip())
                batch.append((
                    str(h.get('player_id', '')),
                    h.get('date'),
                    h.get('rating'),
                    h.get('type', 'singles')
                ))
                
                if len(batch) >= batch_size:
                    conn.executemany(sql, batch)
                    conn.commit()
                    inserted += len(batch)
                    batch.clear()
                    pct = (inserted / total) * 100
                    sys.stdout.write(f"\r   [{pct:.0f}%] Inserted: {inserted:,}/{total:,}")
                    sys.stdout.flush()
            except:
                continue
    
    # Final batch
    if batch:
        conn.executemany(sql, batch)
        conn.commit()
        inserted += len(batch)
    
    conn.close()
    print(f"\r   ✓ Inserted {inserted:,} history records")
    return inserted


def main():
    parser = argparse.ArgumentParser(
        description='Phase 2: Bulk load data from JSONL files into database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python load_data_to_db.py --input-dir ./scrape_output/CAN_adult
    python load_data_to_db.py --input-dir ./scrape_output/CAN_junior --batch-size 5000
        """
    )
    
    parser.add_argument('--input-dir', required=True, help='Directory containing JSONL files')
    parser.add_argument('--batch-size', type=int, default=2000, help='Batch size for inserts (default: 2000)')
    parser.add_argument('--skip-players', action='store_true', help='Skip loading players')
    parser.add_argument('--skip-matches', action='store_true', help='Skip loading matches')
    parser.add_argument('--skip-history', action='store_true', help='Skip loading UTR history')
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.input_dir):
        print(f"❌ Directory not found: {args.input_dir}")
        return
    
    print(f"\n{'='*60}")
    print(f"🎾 UTR Data Loader - Phase 2 (Files to Database)")
    print(f"{'='*60}")
    print(f"   Input: {args.input_dir}")
    print(f"   Batch size: {args.batch_size:,}")
    print()
    
    # Initialize database
    tennis_db.init_db()
    
    stats = {
        'players': 0,
        'matches': 0,
        'history': 0
    }
    
    # Load players
    if not args.skip_players:
        players_file = os.path.join(args.input_dir, 'players.jsonl')
        stats['players'] = bulk_load_players(players_file, batch_size=args.batch_size)
    
    # Load matches
    if not args.skip_matches:
        matches_file = os.path.join(args.input_dir, 'matches.jsonl')
        stats['matches'] = bulk_load_matches(matches_file, batch_size=args.batch_size)
    
    # Load history
    if not args.skip_history:
        history_file = os.path.join(args.input_dir, 'utr_history.jsonl')
        stats['history'] = bulk_load_history(history_file, batch_size=args.batch_size * 2)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"✅ Phase 2 Complete!")
    print(f"{'='*60}")
    print(f"   Players loaded:  {stats['players']:,}")
    print(f"   Matches loaded:  {stats['matches']:,}")
    print(f"   History loaded:  {stats['history']:,}")
    print(f"\n   Database: {DB_FILE}")


if __name__ == "__main__":
    main()
