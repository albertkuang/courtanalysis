import sqlite3
import os
from datetime import datetime

DB_FILE = 'tennis_data.db'

def get_connection():
    """Get a connection to the SQLite database."""
    return sqlite3.connect(DB_FILE, timeout=30.0)

def init_db():
    """Initialize the database tables."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('PRAGMA journal_mode=WAL;')
    
    # Players table
    c.execute('''
    CREATE TABLE IF NOT EXISTS players (
        player_id TEXT PRIMARY KEY,
        name TEXT,
        college TEXT,
        country TEXT,
        gender TEXT,
        utr_singles REAL,
        utr_doubles REAL,
        age INTEGER,
        updated_at TIMESTAMP
    )
    ''')
    
    # Migration: Check if age column exists, if not add it
    c.execute("PRAGMA table_info(players)")
    columns = [row[1] for row in c.fetchall()]
    if 'age' not in columns:
        print("Migrating DB: Adding 'age' column to players table...")
        c.execute("ALTER TABLE players ADD COLUMN age INTEGER")
    if 'location' not in columns:
        print("Migrating DB: Adding 'location' column to players table...")
        c.execute("ALTER TABLE players ADD COLUMN location TEXT")
    if 'pro_rank' not in columns:
        print("Migrating DB: Adding 'pro_rank' column to players table...")
        c.execute("ALTER TABLE players ADD COLUMN pro_rank TEXT")
    if 'age_group' not in columns:
        print("Migrating DB: Adding 'age_group' column to players table...")
        c.execute("ALTER TABLE players ADD COLUMN age_group TEXT")
    
    # Insights Migration (New Metrics)
    if 'comeback_wins' not in columns:
        print("Migrating DB: Adding 'comeback_wins' column...")
        c.execute("ALTER TABLE players ADD COLUMN comeback_wins INTEGER DEFAULT 0")
    if 'year_delta' not in columns:
        print("Migrating DB: Adding 'year_delta' column...")
        c.execute("ALTER TABLE players ADD COLUMN year_delta REAL DEFAULT 0.0")
    if 'tiebreak_wins' not in columns:
        print("Migrating DB: Adding 'tiebreak_wins' column...")
        c.execute("ALTER TABLE players ADD COLUMN tiebreak_wins INTEGER DEFAULT 0")
    if 'tiebreak_losses' not in columns:
        print("Migrating DB: Adding 'tiebreak_losses' column...")
        c.execute("ALTER TABLE players ADD COLUMN tiebreak_losses INTEGER DEFAULT 0")
    if 'three_set_wins' not in columns:
        print("Migrating DB: Adding 'three_set_wins' column...")
        c.execute("ALTER TABLE players ADD COLUMN three_set_wins INTEGER DEFAULT 0")
    if 'three_set_losses' not in columns:
        print("Migrating DB: Adding 'three_set_losses' column...")
        c.execute("ALTER TABLE players ADD COLUMN three_set_losses INTEGER DEFAULT 0")
    
    # Matches table
    # Using specific source_match_id to prevent duplicates from same source
    c.execute('''
    CREATE TABLE IF NOT EXISTS matches (
        match_id TEXT PRIMARY KEY,
        date TEXT,
        winner_id TEXT,
        loser_id TEXT,
        score TEXT,
        tournament TEXT,
        round TEXT,
        source TEXT,
        winner_utr REAL,
        loser_utr REAL,
        processed_player_id TEXT, 
        FOREIGN KEY (winner_id) REFERENCES players (player_id),
        FOREIGN KEY (loser_id) REFERENCES players (player_id)
    )
    ''')
    
    # UTR History table
    c.execute('''
    CREATE TABLE IF NOT EXISTS utr_history (
        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id TEXT,
        date TEXT,
        rating REAL,
        type TEXT,
        FOREIGN KEY (player_id) REFERENCES players (player_id),
        UNIQUE(player_id, date, type)
    )
    ''')
    
    # Index for fast lookups
    c.execute('CREATE INDEX IF NOT EXISTS idx_matches_winner ON matches (winner_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_matches_loser ON matches (loser_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_matches_date ON matches (date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_history_player ON utr_history (player_id)')
    
    conn.commit()
    conn.close()
    print(f"Database {DB_FILE} initialized.")

def save_player(conn, player_data):
    """
    Upsert player data.
    player_data: dict with keys matching table columns
    """
    sql = '''
    INSERT INTO players (player_id, name, college, country, gender, utr_singles, utr_doubles, age, location, pro_rank, age_group, comeback_wins, year_delta, tiebreak_wins, tiebreak_losses, three_set_wins, three_set_losses, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(player_id) DO UPDATE SET
        name=COALESCE(excluded.name, players.name),
        college=COALESCE(excluded.college, players.college),
        country=COALESCE(excluded.country, players.country),
        gender=COALESCE(excluded.gender, players.gender),
        utr_singles=COALESCE(excluded.utr_singles, players.utr_singles),
        utr_doubles=COALESCE(excluded.utr_doubles, players.utr_doubles),
        age=COALESCE(excluded.age, players.age),
        location=COALESCE(excluded.location, players.location),
        pro_rank=COALESCE(excluded.pro_rank, players.pro_rank),
        age_group=COALESCE(excluded.age_group, players.age_group),
        comeback_wins=COALESCE(excluded.comeback_wins, players.comeback_wins),
        year_delta=COALESCE(excluded.year_delta, players.year_delta),
        tiebreak_wins=COALESCE(excluded.tiebreak_wins, players.tiebreak_wins),
        tiebreak_losses=COALESCE(excluded.tiebreak_losses, players.tiebreak_losses),
        three_set_wins=COALESCE(excluded.three_set_wins, players.three_set_wins),
        three_set_losses=COALESCE(excluded.three_set_losses, players.three_set_losses),
        updated_at=excluded.updated_at
    '''
    
    params = (
        str(player_data.get('player_id')),
        player_data.get('name'),
        player_data.get('college'),
        player_data.get('country'),
        player_data.get('gender'),
        player_data.get('utr_singles'),
        player_data.get('utr_doubles'),
        player_data.get('age'),
        player_data.get('location'),
        player_data.get('pro_rank'),
        player_data.get('age_group'),
        player_data.get('comeback_wins'),
        player_data.get('year_delta'),
        player_data.get('tiebreak_wins'),
        player_data.get('tiebreak_losses'),
        player_data.get('three_set_wins'),
        player_data.get('three_set_losses'),
        datetime.now().isoformat()
    )
    
    try:
        conn.execute(sql, params)
    except Exception as e:
        print(f"Error saving player {player_data.get('name')}: {e}")

def save_match(conn, match_data):
    """
    Insert match data.
    match_data: dict with keys matching table columns
    """
    # Auto-create missing players to satisfy foreign keys and populate DB
    winner_id = str(match_data.get('winner_id'))
    loser_id = str(match_data.get('loser_id'))
    winner_name = match_data.get('winner_name', 'Unknown')
    loser_name = match_data.get('loser_name', 'Unknown')
    winner_utr = match_data.get('winner_utr')
    loser_utr = match_data.get('loser_utr')
    
    # Minimal player insert (ignore if exists)
    player_sql = "INSERT OR IGNORE INTO players (player_id, name, utr_singles, updated_at) VALUES (?, ?, ?, ?)"
    try:
        conn.execute(player_sql, (winner_id, winner_name, winner_utr, datetime.now().isoformat()))
        conn.execute(player_sql, (loser_id, loser_name, loser_utr, datetime.now().isoformat()))
    except Exception as e:
        print(f"Warning: Failed to auto-create players for match: {e}")

    sql = '''
    INSERT OR IGNORE INTO matches (match_id, date, winner_id, loser_id, score, tournament, round, source, winner_utr, loser_utr, processed_player_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    params = (
        str(match_data.get('match_id')),
        match_data.get('date'),
        str(match_data.get('winner_id')),
        str(match_data.get('loser_id')),
        match_data.get('score'),
        match_data.get('tournament'),
        match_data.get('round'),
        match_data.get('source'),
        match_data.get('winner_utr'),
        match_data.get('loser_utr'),
        str(match_data.get('processed_player_id'))
    )
    
    try:
        conn.execute(sql, params)
    except Exception as e:
        print(f"Error saving match {match_data.get('match_id')}: {e}")

def save_history(conn, history_data):
    """
    Insert history record.
    history_data: dict with keys matching table columns
    """
    sql = '''
    INSERT OR IGNORE INTO utr_history (player_id, date, rating, type)
    VALUES (?, ?, ?, ?)
    '''
    
    params = (
        str(history_data.get('player_id')),
        history_data.get('date'),
        history_data.get('rating'),
        history_data.get('type')
    )
    
    try:
        conn.execute(sql, params)
    except Exception as e:
        print(f"Error saving history for {history_data.get('player_id')}: {e}")

def get_players_by_name(conn, name_query):
    """Find players matching name."""
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE name LIKE ?", (f"%{name_query}%",))
    columns = [d[0] for d in c.description]
    return [dict(zip(columns, row)) for row in c.fetchall()]

def get_players_by_country(conn, country_code):
    """Find players by country."""
    c = conn.cursor()
    # If country is 'ALL', return all
    if country_code == 'ALL':
        c.execute("SELECT * FROM players")
    else:
        c.execute("SELECT * FROM players WHERE country = ?", (country_code,))
    columns = [d[0] for d in c.description]
    return [dict(zip(columns, row)) for row in c.fetchall()]

def get_player_matches(conn, player_id):
    """Get all matches for a player."""
    c = conn.cursor()
    c.execute('''
        SELECT m.*, 
               w.name as winner_name, 
               l.name as loser_name
        FROM matches m
        LEFT JOIN players w ON m.winner_id = w.player_id
        LEFT JOIN players l ON m.loser_id = l.player_id
        WHERE m.winner_id = ? OR m.loser_id = ?
        ORDER BY date DESC
    ''', (player_id, player_id))
    
    columns = [d[0] for d in c.description]
    return [dict(zip(columns, row)) for row in c.fetchall()]

if __name__ == "__main__":
    init_db()
